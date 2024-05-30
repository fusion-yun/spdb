from __future__ import annotations
import collections
import collections.abc
import pathlib
import typing

import h5py
import numpy
from spdm.core.entry import Entry
from spdm.core.file import File
from spdm.core.path import Path
from spdm.utils.logger import logger
from spdm.utils.tags import _undefined_

SPDM_LIGHTDATA_MAX_LENGTH = 3


def h5_require_group(grp, path):
    if isinstance(path, str):
        path = path.split("/")

    for p in path:
        if isinstance(p, str):
            pass
        elif isinstance(p, int):
            if p < 0:
                num = len(grp)
                p = p % num
            p = f"__index__{p}"
        if grp is not None:
            grp = grp.require_group(p)
        else:
            raise KeyError(f"Cannot create group for {p}")

    return grp


def h5_put_value(grp, path, value):
    res = None
    if path is None:
        path = []
    elif isinstance(path, Path):
        path = path[:]
    elif not isinstance(path, list):
        path = [path]

    if isinstance(value, collections.abc.Mapping):
        grp = h5_require_group(grp, path)
        for k, v in value.items():
            h5_put_value(grp, [k], v)
    elif len(path) == 0:
        raise KeyError(f"Empty path!")
    else:
        grp = h5_require_group(grp, path[:-1])
        path = path[-1]

        if isinstance(path, int):
            path = f"__index__{path}"
        # elif not isinstance(path, str):
        #     raise KeyError(path)
        if path != "" and path in grp.keys():
            del grp[path]

        if type(value) is list:
            array_value = numpy.array(value)

            if array_value.dtype.type is numpy.object_:
                grp = h5_require_group(grp, path)

                grp.attrs["__is_list__"] = True

                for idx, v in enumerate(value):
                    h5_put_value(grp, idx, v)

            elif array_value.dtype.type is numpy.unicode_:
                # h5py does not support unicode string.
                array_value = array_value.astype(h5py.special_dtype(vlen=str))
                h5_put_value(grp, path, array_value)
            else:
                h5_put_value(grp, path, array_value)
        elif type(value) is numpy.ndarray and len(value) > SPDM_LIGHTDATA_MAX_LENGTH:
            grp[path] = value
        else:  # type(value) in [str, int, float]:
            grp.attrs[path] = value

    return res


def h5_get_value(obj, path=None, projection=None, default=_undefined_, **kwargs):
    if path is None:
        path = []
    elif isinstance(path, Path):
        path = path[:]
    elif not isinstance(path, list):
        path = [path]

    if obj is None:
        raise RuntimeError("None group")

    prefix = []
    if path is not None:
        for p in path:
            if isinstance(p, str):
                pass
            elif isinstance(p, int):
                if p < 0:
                    num = len(grp)
                    p = p % num
                p = f"__index__{p}"

            prefix.append(p)

            if p in obj:
                obj = obj[p]
            elif p in obj.attrs:
                obj = obj.attrs[p]
            else:
                raise KeyError(f"Can not search element at {'/'.join(prefix)} !")

    if projection is None:
        if isinstance(obj, h5py.Group):
            if obj.attrs.get("__is_list__", False):
                res = [h5_get_value(obj[k]) for k in obj]
            else:
                res = {**(h5_get_value(obj.attrs)), **{k: h5_get_value(obj[k]) for k in obj}}
        elif isinstance(obj, h5py.AttributeManager):
            res = {k: h5_get_value(obj[k]) for k in obj if not k.startswith("__")}
        elif isinstance(obj, h5py.Dataset):
            res = obj[:]
        else:
            res = obj
    elif isinstance(projection, str):
        if isinstance(obj, h5py.Group):
            res = h5_get_value(obj.attrs, projection) or h5_get_value(obj.get(projection, None))
        elif isinstance(obj, h5py.AttributeManager):
            res = h5_get_value(obj.get(projection, None))

    elif isinstance(obj, h5py.Group):
        if obj.attrs.get("__is_list__", False):
            res = []
        else:
            res = {
                **h5_get_value(obj.attrs, projection),
                **{k: h5_get_value(obj[k]) for k, v in projection.items() if v > 0 and k in obj},
            }
    elif isinstance(obj, h5py.AttributeManager):
        res = {k: h5_get_value(obj[k]) for k, v in projection.items() if v > 0 and k in obj}
    elif isinstance(obj, h5py.Dataset):
        res = obj[:]
    else:
        res = obj

    return res


def h5_dump(grp):
    return h5_get_value(grp, [])


@File.register(["h5", "hdf5", "HDF5"])
class HDF5File(File):
    MOD_MAP = {
        File.Mode.read: "r",
        File.Mode.read | File.Mode.write: "r+",
        File.Mode.write: "w-",
        File.Mode.write | File.Mode.create: "w",
        File.Mode.read | File.Mode.write | File.Mode.create: "a",
    }

    """
        r       Readonly, file must exist (default)
        r+      Read/write, file must exist
        w       Create file, truncate if exists
        w- or x Create file, fail if exists
        a       Read/write if exists, create otherwise
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fid = None

    @property
    def mode_str(self) -> str:
        return HDF5File.MOD_MAP[self.mode]

    def open(self) -> File:
        if self.is_open:
            return self

        try:
            if self._fid is None:
                self._fid = h5py.File(self.path, mode=self.mode_str)
        except OSError as error:
            raise FileExistsError(f"Can not open file {self.path}! {error}")
        else:
            logger.debug(f"Open HDF5 File {self.path} mode={self.mode}")

        super().open()

        return self

    def close(self):
        if not self.is_open:
            return
        if self._fid is not None:
            self._fid.close()
        self._fid = None
        return super().close()

    @property
    def entry(self) -> Entry:
        return H5Entry(self.open())

    def read(self, lazy=True) -> Entry:
        return H5Entry(self.open())

    def write(self, *args, **kwargs):
        H5Entry(self.open()).insert(*args, **kwargs)


@Entry.register(["h5", "hdf5", "HDF5"])
class H5Entry(Entry):
    def __init__(self, uri: str | HDF5File, *args, **kwargs):
        super().__init__(None, *args, **kwargs)

        if isinstance(uri, str):
            self._file = HDF5File(uri)
        elif isinstance(uri, File):
            self._file = uri
        else:
            raise TypeError(f"cache must be HDF5File or str, but got {type(uri)}")

        self._data = self._file._fid

    def __copy_from__(self, other: H5Entry) -> Entry:
        super().__copy_from__(other)
        self._file = other._file
        return self

    @property
    def is_writable(self) -> bool:
        return "r" in self._data.is_writable

    def copy(self, other):
        if isinstance(other, Entry):
            other = other.entry.__real_value__()
        self.put(None, other)

    # def put(self, path, value, *args, **kwargs):
    #     return h5_put_value(self._cache, path, value)

    # def get(self, path=[], projection=None, *args, **kwargs):
    #     return h5_get_value(self._cache, path, projection=projection)

    def insert(self, value, *args, **kwargs):
        return h5_put_value(self._data, self._path, value, *args, **kwargs)

    def find(self, *args, **kwargs) -> typing.Any:
        return h5_get_value(self._data, self._path, *args, **kwargs)

    def dump(self):
        return h5_dump(self._data)

    def iter(self, path, *args, **kwargs):
        raise NotImplementedError()


# class HDF5Collection(FileCollection):
#     def __init__(self, uri, *args, **kwargs):
#         super().__init__(uri, *args,
#                          file_extension=".h5",
#                          file_factory=lambda *a, **k: H5File(*a, **k),
#                          ** kwargs)
