from __future__ import annotations

import collections.abc
import pathlib
import typing


from ..utils.logger import logger
from ..utils.uri_utils import URITuple, uri_split
from .document import Document
from .entry import Entry


class File(Document):
    """
    File like object
    """

    def __init__(self, url: str | pathlib.Path | URITuple, *args, format=None, default_format=None, **kwargs):
        if self.__class__ is File:
            if format is not None:
                format = format.lower()
            elif isinstance(url, dict):
                format = url.get("$class", "").lower()
            elif isinstance(url, pathlib.PosixPath):
                format = url.suffix[1:].lower()
            elif isinstance(url, (str, URITuple)):
                uri = uri_split(url)
                schemes = uri.protocol.split("+") if uri.protocol != "" and uri.protocol != None else []
                if len(schemes) == 0:
                    pass
                elif schemes[0] in ["file", "local"]:
                    format = "+".join(schemes[1:])

                if format is None or format == "":
                    format = pathlib.PosixPath(uri.path).suffix[1:]

            super().__dispatch_init__([format, default_format], self, url, *args, **kwargs)

            return

        super().__init__(url, *args, **kwargs)
        self._is_open = False

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

    # @property
    # def entry(self) -> Entry: return FileEntry(file=self)

    def __enter__(self) -> Document:
        return super().__enter__()

    def read(self, lazy=False) -> Entry:
        raise NotImplementedError(f"TODO: {self.__class__.__name__}.read")

    def write(self, data=None, *args, lazy=False, **kwargs):
        raise NotImplementedError(f"TODO: {self.__class__.__name__}.write")


class FileEntry(Entry):
    def __init__(self, *args, file, **kwargs):
        super().__init__(*args, **kwargs)
        self._fid = file

    def __copy_from__(self, other: FileEntry) -> Entry:
        super().__copy_from__(other)
        self._fid = other._fid
        return self

    # def __del__(self):
    #     if len(self._path) == 0:
    #         self.flush()

    def flush(self):
        logger.debug(self._data)
        self._fid.write(self._data)
        self._data = None
