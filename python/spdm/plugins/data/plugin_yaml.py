import collections
import typing
import numpy
import yaml
from spdm.core.entry import Entry
from spdm.core.file import File
from spdm.utils.logger import logger
from spdm.utils.typing import as_native


# class YAMLDocument(Document):
#     def __init__(self, path, *args, **kwargs):
#         super().__init__(path, *args, **kwargs)
#         self.load(path, mode=self.mode)

#     def load(self, *args, **kwargs):
#         with self.open(mode="r") as fid:
#             if fid is not None:
#                 self._holder = yaml.load(fid, Loader=yaml.CLoader)
#             else:
#                 self._holder = None

#     def save(self, d, *args, **kwargs):
#         with self.open(mode="w") as fid:
#             yaml.dump(self._holder, fid,  Dumper=yaml.CDumper)


# class YAMLCollection(Collection):
#     def __init__(self, uri, *args, **kwargs):
#         super().__init__(uri, *args,
#                          file_extension=".json",
#                          file_factory=lambda *a, **k: YAMLDocument(*a, **k),
#                          ** kwargs)


@File.register(["yaml", "YAML"])
class FILEPLUGINyaml(File):
    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fid: typing.Optional[typing.IO[typing.Any]] = None

    def open(self) -> File:
        super().open()
        try:
            self._fid = open(self.path,  mode=self.mode_str)
        except OSError as error:
            raise FileExistsError(f"Can not open file {self.path}! {error}")
        else:
            logger.debug(
                f"Open {self.__class__.__name__} File {self.path} mode={self.mode}")
        return self

    def close(self):
        if self._fid is not None:
            self._fid.close()
            self._fid = None
        return super().close()

    def read(self, *args,   **kwargs) -> Entry:
        if not hasattr(self, "_fid"):
            self.open()
        return Entry(yaml.load(self._fid, Loader=yaml.CLoader))

    def write(self,   d, *args,  **kwargs):
        yaml.dump(as_native(d, enable_ndarray=False), self._fid,  Dumper=yaml.CDumper)


__SP_EXPORT__ = FILEPLUGINyaml
