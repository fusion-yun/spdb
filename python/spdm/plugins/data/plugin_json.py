import json
import typing

from spdm.core.entry import Entry
from spdm.core.file import File
from spdm.utils.typing import as_native
from spdm.utils.logger import logger


@File.register(["json", "JSON"])
class FILEPLUGINjson(File):
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
        return Entry(json.load(self._fid))

    def write(self,   d, *args,  **kwargs):
        json.dump(as_native(d, enable_ndarray=False), self._fid)


__SP_EXPORT__ = FILEPLUGINjson
