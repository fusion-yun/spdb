from __future__ import annotations

import pathlib


from spdm.utils.logger import logger
from spdm.utils.uri_utils import URITuple, uri_split
from spdm.core.document import Document
from spdm.core.entry import Entry


class File(Document):
    """
    File like object
    """

    def __new__(cls, url, *args, scheme=None, default_scheme=None, **kwargs):
        if cls is not File:
            return super().__new__(cls)

        if scheme is not None:
            scheme = scheme.lower()
        elif isinstance(url, dict):
            scheme = url.get("$class", "").lower()
        elif isinstance(url, pathlib.PosixPath):
            scheme = url.suffix[1:].lower()
        elif isinstance(url, (str, URITuple)):
            url = uri_split(url)
            schemes = url.protocol.split("+") if url.protocol != "" and url.protocol is not None else []
            if len(schemes) == 0:
                pass
            elif schemes[0] in ["file", "local"]:
                scheme = "+".join(schemes[1:])

            if scheme is None or scheme == "":
                scheme = pathlib.PosixPath(url.path).suffix[1:]
        if scheme is None:
            scheme = default_scheme

        return super().__new__(cls, scheme=scheme)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fid = None

    def __del__(self):
        fid = getattr(self, "_fid", None)
        if fid is not None:
            fid.close()
            self._fid = None

    @property
    def mode_str(self) -> str:
        return File.MOD_MAP.get(self.mode, "r")

    @property
    def is_writable(self) -> bool:
        return self.mode | File.Mode.write > 0

    @property
    def is_opened(self) -> bool:
        return self._fid is not None

    def __enter__(self) -> Document:
        return super().__enter__()

    def read(self) -> Entry:
        raise NotImplementedError(f"TODO: {self.__class__.__name__}.read")

    def write(self, *args, **kwargs):
        raise NotImplementedError(f"TODO: {self.__class__.__name__}.write")


class FileEntry(Entry):
    def __init__(self, *args, file, **kwargs):
        super().__init__(*args, **kwargs)
        self._fid = file

    def __copy__(self) -> Entry:
        other = super().__copy__()
        other._fid = self._fid
        return other

    # def __del__(self):
    #     if len(self._path) == 0:
    #         self.flush()

    def flush(self):
        logger.debug(self._data)
        self._fid.write(self._data)
        self._data = None
