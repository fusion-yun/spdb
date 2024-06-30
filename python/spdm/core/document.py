from __future__ import annotations
import typing
from enum import Flag, auto

from spdm.utils.uri_utils import URITuple, uri_split
from spdm.utils.tags import _not_found_

from spdm.core.entry import Entry as EntryBase
from spdm.core.entry import open_entry


class Document:
    """
    Connection like object
    """

    class Entry(EntryBase):
        def __init__(self, root: URITuple = None, **kwargs):
            self._root = root
            super().__init__(_not_found_, **kwargs)

        @property
        def uri(self) -> URITuple:
            return f"{self._root.uri}#{self._path}"

        def __copy__(self) -> typing.Self:
            other = super().__copy__()
            other._root = self._root
            return other

        def flush(self):
            self._root.write(self._path, self._cache)
            self._cache = _not_found_

    class Mode(Flag):
        """
        r       Readonly, file must exist (default)
        r+      Read/write, file must exist
        w       Create file, truncate if exists
        w- or x Create file, fail if exists
        a       Read/write if exists, create otherwise
        """

        read = auto()  # open for reading (default)
        write = auto()  # open for writing, truncating the file first
        create = auto()  # open for exclusive creation, failing if the file already exists
        append = read | write | create
        temporary = auto()  # is temporary

    MOD_MAP = {
        Mode.read: "r",
        Mode.read | Mode.write: "rw",
        Mode.write: "x",
        Mode.write | Mode.create: "w",
        Mode.read | Mode.write | Mode.create: "a",
    }
    INV_MOD_MAP = {
        "r": Mode.read,
        "rw": Mode.read | Mode.write,
        "x": Mode.write,
        "w": Mode.write | Mode.create,
        "a": Mode.read | Mode.write | Mode.create,
    }

    def __init__(self, uri, mode: typing.Any = Mode.read, **kwargs):
        """
        r       Readonly, file must exist (default)
        rw      Read/write, file must exist
        w       Create file, truncate if exists
        x       Create file, fail if exists
        a       Read/write if exists, create otherwise
        """

        self._uri = uri_split(uri)
        self._mode = Document.INV_MOD_MAP[mode] if isinstance(mode, str) else mode
        self._metadata = kwargs
        self._entry = None

    def __str__(self):
        return f"<{self.__class__.__name__}  {self._uri} >"

    @property
    def uri(self) -> URITuple:
        return self._uri

    @property
    def path(self) -> typing.Any:
        return self._uri.path

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def is_ready(self) -> bool:
        return self._entry is not None

    @property
    def is_readable(self) -> bool:
        return bool(self._mode & Document.Mode.read)

    @property
    def is_writable(self) -> bool:
        return bool(self._mode & Document.Mode.write)

    @property
    def is_creatable(self) -> bool:
        return bool(self._mode & Document.Mode.create)

    @property
    def is_temporary(self) -> bool:
        return bool(self._mode & Document.Mode.temporary)

    def open(self) -> Entry:
        if self._entry is None:
            self._entry = open_entry(self._uri, **self._metadata)
        return self._entry

    def close(self) -> None:
        self._entry = None

    def __del__(self):
        self.close()

    def __enter__(self) -> Entry:
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.close()

    def __entry__(self) -> Entry:
        return self._entry

    @property
    def entry(self) -> Entry:
        return self.__entry__()

    def read(self, *args, **kwargs) -> typing.Any:
        "读取"
        return self.__entry__().find(*args, **kwargs)

    def write(self, *args, **kwargs):
        "写入"
        return self.__entry__().update(*args, **kwargs)
