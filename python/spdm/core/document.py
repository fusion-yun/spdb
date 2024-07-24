import typing

from enum import Flag, auto

from spdm.utils.uri_utils import URITuple, uri_split
from spdm.utils.tags import _not_found_

from spdm.core.pluggable import Pluggable
from spdm.core.entry import Entry as EntryBase


class Document(Pluggable, plugin_prefix="spdm/plugins/data/"):
    """Connection like object"""

    _plugin_registry = {}

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

    class Entry(EntryBase):

        def __init__(self, doc, *args, **kwargs):
            super().__init__(_not_found_, *args, **kwargs)
            if doc is not _not_found_ and not isinstance(doc, Document):
                raise TypeError(f"doc must be an instance of Document, not {type(doc)}")
            self._doc = doc

        def __str__(self):
            return f"{self._doc.uri}#{self._path}"

        def __copy__(self) -> typing.Self:
            other = super().__copy__()
            other._doc = self._doc
            return other

        def find(self, *args, default_value=_not_found_, **kwargs) -> typing.Any:
            res = _not_found_
            if self._cache is not _not_found_:
                res = super().find(*args, default_value=_not_found_, **kwargs)

            if res is _not_found_:
                res = self._doc.read(self._path, *args, default_value=default_value, **kwargs)
                if len(args) + len(kwargs) == 0:
                    self._cache = self._path.update(self._cache, res)

            return res

        def update(self, *args, **kwargs) -> None:
            return super().update(*args, **kwargs)

        def read(self, *args, **kwargs) -> typing.Any:
            return self.find(*args, **kwargs)

        def write(self, *args, **kwargs) -> None:
            self.update(*args, **kwargs)
            self.flush()

        def flush(self):
            """将缓存内的数据写入持久存储（文件）"""
            self._doc.write(self._path, self._cache)
            # self._cache = _not_found_

        def load(self):
            """将持久存储（文件）导入缓存"""
            self._cache = self._path.update(self._cache, self._doc.read(self._path))

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

    # @property
    # def is_ready(self) -> bool:
    #     return self._entry is not None

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

    # -----------------------------------------------------------------------------
    def open(self) -> Entry:
        """打开文档"""
        # logger.verbose(f"File {self._uri} is opened!")
        return self.__class__.Entry(self)

    def close(self) -> None:
        """关闭文档"""
        # logger.verbose(f"File {self._uri} is closed!")

    def __entry__(self) -> Entry:
        return self.open()

    # -----------------------------------------------------------------------------

    @typing.final
    def __del__(self):
        self.close()

    @typing.final
    def __enter__(self) -> Entry:
        return self.open()

    @typing.final
    def __exit__(self, exc_type, exc_value, traceback):
        return self.close()

    @property
    def entry(self) -> Entry:
        return self.__entry__()

    def read(self, *args, **kwargs) -> typing.Any:
        "读取"
        return NotImplemented

    def write(self, *args, **kwargs) -> None:
        "写入"
