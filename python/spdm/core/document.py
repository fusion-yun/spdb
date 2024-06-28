from __future__ import annotations
import abc
import typing
from enum import Flag, auto

from spdm.utils.uri_utils import URITuple, uri_split
from spdm.utils.tags import _not_found_

from spdm.core.entry import Entry as EntryBase


class Document:
    """
    Connection like object
    """

    class Entry(EntryBase):
        def __init__(self, doc, *args, **kwargs):
            super().__init__(_not_found_, *args, **kwargs)
            self._doc = doc

        def __copy__(self) -> typing.Self:
            other = super().__copy__()
            other._doc = self._doc
            return other

        def flush(self):
            self._doc.write(self._path, self._cache)
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

        self._url = uri_split(uri)
        self._mode = Document.INV_MOD_MAP[mode] if isinstance(mode, str) else mode
        self._entry = self.__class__.Entry(uri, *args, **kwargs)

    def __str__(self):
        return f"<{self.__class__.__name__}  {self.url} >"

    @property
    def url(self) -> URITuple:
        return self._url

    @property
    def path(self) -> typing.Any:
        return self.url.path

    @property
    def mode(self) -> Mode:
        return self._mode

    # @property
    # def mode_str(self) -> str:
    #     return ''.join([(m.name[0]) for m in list(Connection.Mode) if m & self._mode])
    @property
    def is_ready(self) -> bool:
        return False

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

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def __del__(self):
        self.close()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.close()

    def __enter__(self) -> Entry:
        return self.entry

    @property
    def entry(self) -> Entry:
        return self._entry if self._entry is not None else self.__class__.Entry(self)

    def read(self, *args, **kwargs) -> typing.Any:
        "读取"
        return self.entry.find(*args, **kwargs)

    def write(self, *args, **kwargs):
        "写入"
        return self.entry.update(*args, **kwargs)
