from __future__ import annotations

import typing
from enum import Flag, auto

from ..utils.plugin import Pluggable
from ..utils.uri_utils import URITuple, uri_split
from .entry import Entry


class Document(Pluggable):
    """
        Connection like object
    """
    _plugin_registry = {}
    _plugin_prefix = "spdm.plugins.data.plugin_"

    class Mode(Flag):
        read = auto()       # open for reading (default)
        write = auto()      # open for writing, truncating the file first
        create = auto()     # open for exclusive creation, failing if the file already exists
        append = read | write | create
        temporary = auto()  # is temporary
    """
        r       Readonly, file must exist (default)
        r+      Read/write, file must exist
        w       Create file, truncate if exists
        w- or x Create file, fail if exists
        a       Read/write if exists, create otherwise
    """
    MOD_MAP = {Mode.read: "r",
               Mode.read | Mode.write: "rw",
               Mode.write: "x",
               Mode.write | Mode.create: "w",
               Mode.read | Mode.write | Mode.create: "a",
               }
    INV_MOD_MAP = {"r": Mode.read,
                   "rw": Mode.read | Mode.write,
                   "x": Mode.write,
                   "w": Mode.write | Mode.create,
                   "a": Mode.read | Mode.write | Mode.create,
                   }

    class Status(Flag):
        opened = auto()
        closed = auto()

    def __init__(self, uri, *args, mode: typing.Any = Mode.read, **kwargs):
        """
         r       Readonly, file must exist (default)
         rw      Read/write, file must exist
         w       Create file, truncate if exists
         x       Create file, fail if exists
         a       Read/write if exists, create otherwise
        """
        if self.__class__ is Document:
            return Document.__dispatch_init__(None, self, uri, *args, **kwargs)

        self._url = uri_split(uri)
        self._mode = Document.INV_MOD_MAP[mode] if isinstance(mode, str) else mode
        self._is_open = False

    def __del__(self):
        if getattr(self, "_is_open", False):
            self.close()

    def __str__(self): return f"<{self.__class__.__name__}  {self.url} >"

    @property
    def url(self) -> URITuple: return self._url

    @property
    def path(self) -> typing.Any: return self.url.path 

    @property
    def mode(self) -> Mode: return self._mode

    # @property
    # def mode_str(self) -> str:
    #     return ''.join([(m.name[0]) for m in list(Connection.Mode) if m & self._mode])

    @property
    def is_readable(self) -> bool: return bool(self._mode & Document.Mode.read)

    @property
    def is_writable(self) -> bool: return bool(self._mode & Document.Mode.write)

    @property
    def is_creatable(self) -> bool: return bool(self._mode & Document.Mode.create)

    @property
    def is_temporary(self) -> bool: return bool(self._mode & Document.Mode.temporary)

    @property
    def is_open(self) -> bool: return self._is_open

    def open(self) -> Document:
        self._is_open = True
        return self

    def close(self) -> None:
        self._is_open = False


    def __enter__(self) -> Document: return self.open()

    def __exit__(self, exc_type, exc_value, traceback): return self.close()

    def read(self, lazy=False) -> Entry: raise NotImplementedError()

    def write(self, data=None, lazy=False, **kwargs) -> Entry: raise NotImplementedError()

    @property
    def entry(self) -> Entry: raise NotImplementedError()
