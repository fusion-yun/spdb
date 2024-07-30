import collections
import collections.abc

import pathlib
import typing
import netCDF4 as nc
import numpy as np
from spdm.utils.logger import logger
from spdm.utils.tags import _undefined_, _not_found_
from spdm.core.entry import Entry
from spdm.core.file import File
from spdm.core.path import Path

SPDM_LIGHTDATA_MAX_LENGTH = 64


def nc_put_value(grp, path, value, **kwargs):
    res = None
    path = Path(path)
    if isinstance(value, collections.abc.Mapping):
        for k, v in value.items():
            nc_put_value(grp, path / k, v, **kwargs)
    elif isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
        if all(map(lambda v: isinstance(v, (int, float)), value)):
            value = np.array(value)
            nc_put_value(grp, path, value, **kwargs)
        else:
            for k, v in enumerate(value):
                nc_put_value(grp, path / k, v)
    elif type(value) is np.ndarray and len(value) > SPDM_LIGHTDATA_MAX_LENGTH:
        parent = path.parent.__str__()
        key = path[-1]
        if len(parent) == 0:
            parent = grp
        else:
            parent = grp.createGroup(parent)

        dimensions = []
        for idx, d in enumerate(value.shape):
            parent.createDimension(f"{key}__dim_{idx}", d)
            dimensions.append(f"{key}__dim_{idx}")

        d = parent.createVariable(path.as_url(), value.dtype, tuple(dimensions))
        d[:] = value

    else:  # type(value) in [str, int, float]:
        p = path.parent.as_url()
        if len(p) > 0:
            obj = grp.createGroup(p)
        else:
            obj = grp

        obj.setncattr(path[-1], value)
    return


def nc_get_value(grp, path, projection=None, default=_not_found_, **kwargs):

    if grp is None:
        raise RuntimeError("None group")

    path = Path(path)[:]
    obj = grp
    for pos, p in enumerate(path):
        if isinstance(p, str):
            if p in obj.groups():
                obj = obj[p]
            elif p in obj.ncattrs() and pos == len(path) - 1:
                obj = obj.getncattr(p)
            else:
                raise IndexError(path[: pos + 1])

    if isinstance(obj, (nc.Group, nc.Dataset)):
        res1 = {k: nc_get_value(v, []) for k, v in obj.groups.items()}
        res2 = {k: nc_get_value(v, []) for k, v in obj.variables.items()}
        res3 = {k: obj.getncattr(k) for k in obj.ncattrs()}
        res = {**res1, **res2, **res3}
    elif isinstance(obj, nc.Variable):
        res = obj[:]
    else:
        res = obj

    return res


def nc_dump(grp):
    return nc_get_value(grp, [])


class NetCDFEntry(Entry):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def copy(self, other):
        if hasattr(other, "__entry__"):
            other = other.__entry__.__value__()
        self.update(other)

    def insert(self, value, *args, **kwargs):
        return nc_put_value(self._cache, self._path, value, *args, **kwargs)

    def find(self, *args, **kwargs) -> typing.Any:
        return nc_get_value(self._cache, self._path, *args, **kwargs)

    def dump(self):
        return nc_dump(self._cache)

    def iter(self, path, *args, **kwargs):
        raise NotImplementedError()


class FILEPLUGINnetcdf(File, plugin_name=["nc", "netcdf", "NetCDf"]):

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
        return FILEPLUGINnetcdf.MOD_MAP[self.mode]

    def open(self) -> File:
        if self.is_open:
            return self

        try:
            if self._fid is None:
                self._fid = nc.Dataset(self.path, self.mode_str, format="NETCDF4")
        except OSError as error:
            raise FileExistsError(f"Can not open file {self.path}! {error}")
        else:
            logger.debug(f"Open NetCDF File {self.path} mode={self.mode}")

        super().open()

        return self

    def close(self):
        if not self.is_open:
            return
        if self._fid is not None:
            self._fid.close()
        self._fid = None
        return super().close()

    def read(self, lazy=True) -> Entry:
        return NetCDFEntry(self.open()._fid)

    def write(self, *args, **kwargs):
        NetCDFEntry(self.open()._fid).insert(*args, **kwargs)


# class NetCDFCollection(FileCollection):
#     def __init__(self, uri, *args, **kwargs):
#         super().__init__(uri, *args,
#                          file_extension=".h5",
#                          file_factory=lambda *a, **k: NCFile(*a, **k),
#                          ** kwargs)

__SP_EXPORT__ = FILEPLUGINnetcdf
