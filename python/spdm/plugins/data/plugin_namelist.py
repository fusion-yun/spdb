import collections
import collections.abc
import typing
import pathlib
import f90nml
import numpy as np
from spdm.core.file import File
from spdm.core.entry import Entry
from spdm.utils.tree_utils import normalize_data
from spdm.utils.logger import logger

# class NumpyEncoder(json.NAMELISTEncoder):
#     def default(self, obj):
#         if isinstance(obj, np.ndarray):
#             return obj.tolist()

#         logger.debug(type(obj))
# #         return super().default(obj)


# class NAMELISTFile(File):
#     def __init__(self, path, *args, **kwargs):
#         super().__init__(path, *args, **kwargs)
#         self._path = path

#     def load(self, *args, path=None,  **kwargs):
#         with open(path or self._path, mode="r") as fid:
#             self.root._holder = f90nml.read(fid).todict(complex_tuple=True)

#     def save(self,   *args, path=None, template=None, **kwargs):
#         with open(path or self._path, mode="w") as fid:
#             d = self._encode("", self.root._holder)
#             if template is None:
#                 f90nml.write(d, fid)
#             else:
#                 if isinstance(template, str):
#                     template = urisplit(template)
#                 f90nml.patch(template.path, d, fid)

#     def _encode(self, prefix, nobj):
#         if isinstance(nobj, str):
#             return nobj
#         elif isinstance(nobj, collections.abc.Mapping):
#             return {k: self._encode(f"{prefix}.{k}", p) for k, p in nobj.items()}
#         elif isinstance(nobj, collections.abc.Sequence):
#             return [self._encode(f"{prefix}.{k}", p) for k, p in enumerate(nobj)]
#         elif type(nobj) not in [str, int, float, bool, type(None)]:
#             return str(nobj)
#         else:
#             return nobj

@File.register(["namelist"])
class NAMELISTFile(File):
    def __init__(self,  *args, template: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._template = pathlib.Path(template) if template is not None else None

    def write(self, data=None, *args, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, collections.abc.Mapping) or self._template is None:
            super().write(data, *args, **kwargs)
        else:
            data = normalize_data(data)
            f90nml.patch(self._template.as_posix(), data, self.path.as_posix())

    def read(self) -> Entry:
        with open(self.path, mode="r") as fid:
            data: dict = f90nml.read(fid).todict(complex_tuple=True)
        return Entry(data)
