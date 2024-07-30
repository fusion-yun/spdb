""" Entry class to manage data."""

import pathlib
import typing
from copy import copy

from functools import singledispatch

from spdm.utils.tags import _not_found_, _undefined_
from spdm.utils.uri_utils import URITuple, uri_split
from spdm.core.path import Path, as_path, Query

from spdm.utils.logger import logger


class Entry:  # pylint: disable=R0904
    """Entry class to manage data.
    数据入口类，用于管理多层树状（Hierarchical Tree Structured Data）数据访问。提供操作：
    - insert: 插入数据
    - update: 更新数据
    - delete: 删除数据
    - find: 查找数据
    - search: 搜索/遍历数据


    Open an Entry from a URL.

    Using urllib.urlparse to parse the URL.  rfc3986

    URL format: <protocol>://<authority>/<path>?<query>#<fragment>

    RF3986 = r"^((?P<protocol>[^:/?#]+):)?(//(?P<authority>[^/?#]*))?(?P<path>[^?#]*)(\\?(?P<query>[^#]*))?(#(?P<fragment>.*))?")

    Example:
        ../path/to/file.json                    => File
        file:///path/to/file                    => File
        ssh://a.b.c.net/path/to/file            => ???
        https://a.b.c.net/path/to/file          => ???

        imas+ssh://a.b.c.net/path/to/file

        east+mdsplus://<mds_prefix>
        east+mdsplus+ssh://<mds_prefix>


    """

    def __init__(self, *args, _plugin_name=None):
        self._cache = _not_found_ if len(args) == 0 else args[0]
        self._path: Path = as_path(*args[1:])

    def __copy__(self) -> typing.Self:
        other = object.__new__(self.__class__)
        other._cache = self._cache
        other._path = copy(self._path)
        return other

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} path="{self._path}" />'

    def __repr__(self) -> str:
        return str(self._path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_root(self) -> bool:
        return self._path is None or len(self._path) == 0

    @property
    def root(self) -> typing.Self:
        other = copy(self)
        other._path = []  # pylint: disable=W0212
        return other

    @property
    def parent(self) -> typing.Self:
        other = copy(self)
        other._path = other._path.parent  # pylint: disable=W0212
        return other

    def child(self, *args) -> typing.Self:
        path = as_path(*args)
        if len(path) == 0:
            return self

        if self._cache is not None or len(self._path) == 0:
            pass
        elif isinstance(self._path[0], str):
            self._cache = {}
        else:
            self._cache = []

        other = copy(self)
        other._path.append(path)  # pylint: disable=W0212
        return other

    ###########################################################
    # API: CRUD  operation

    def insert(self, *args, **kwargs):
        """插入数据到 entry 所指定位置。 TODO: 返回修改处的entry"""
        self.child(Path.tags.append).update(*args, **kwargs)

    def update(self, *args, **kwargs):
        """更新 entry 所指定位置的数据。 TODO: 返回修改处的entry"""
        self._cache = self._path.update(self._cache, *args, **kwargs)

    def delete(self, *args, **kwargs):
        """删除 entry 所指定位置的数据"""
        self._path.delete(self._cache, *args, **kwargs)

    def find(self, *p_args, **p_kwargs) -> typing.Any:
        """返回 entry 所指定位置的数据"""
        return self._path.find(self._cache, *p_args, **p_kwargs)

    def search(self, *p_args, **p_kwargs) -> typing.Generator[typing.Self, None, None]:
        """搜索 entry 所指定位置处符合条件的节点

        Usage:
        - 遍历所有子节点 entry
            `entry.search() `

        - 遍历满足条件 condition 的子节点 entry, kwargs视为 condition
            `entry.search()`
            `entry.search()`

        - 遍历满足条件 cond 的子节点，并返回 projection(value,*parameters,**kwargs)的结果
            entry.search(condition,*projection, **kwargs)
        """
        yield from self._path.search(self._cache, *p_args, **p_kwargs)

    # -----------------------------------------------------------
    # alias
    @typing.final
    def query(self, *args, **kwargs) -> typing.Any:
        """alias of find"""
        return self.find(*args, **kwargs)

    @typing.final
    def keys(self) -> typing.Generator[str, None, None]:
        yield from self.search(None, Query.tags.get_key)  # type:ignore

    @typing.final
    def values(self) -> typing.Generator[typing.Any, None, None]:
        yield from self.search(None, Query.tags.get_value)  # type:ignore

    @typing.final
    def for_each(self) -> typing.Generator[typing.Self, None, None]:
        """alis of search"""
        yield from self.search()

    @typing.final
    def append(self, value) -> None:
        self.insert(value)

    @typing.final
    def __setitem__(self, key, value) -> None:
        return self.put(key, value)

    @typing.final
    def __getitem__(self, key) -> typing.Self:
        return self.child(key)

    @typing.final
    def get(self, path=None, default_value=_not_found_) -> typing.Any:
        return self.child(path).find(default_value=default_value)

    @typing.final
    def put(self, *args, **kwargs) -> None:
        return self.child(*args[:-1]).update(*args[-1:], **kwargs)

    @property
    def empty(self) -> bool:
        return self._cache is _not_found_ or len(self._cache) == 0

    @property
    def is_leaf(self) -> bool:
        return self.query(Query.is_leaf)

    @property
    def is_list(self) -> bool:
        return self.query(Query.is_list)

    @property
    def is_dict(self) -> bool:
        return self.query(Query.is_dict)

    @property
    def value(self) -> typing.Any:
        return self.get()

    @property
    def count(self) -> int:
        return self.query(Query.count)

    @property
    def exists(self) -> bool:
        return self.query(Query.exists)

    def check_type(self, tp: typing.Type) -> bool:
        return self.query(Query.check_type, tp)

    def equal(self, other) -> bool:
        if isinstance(other, Entry):
            return self.query(Query.equal, other.__value__)
        return self.query(Query.equal, other)

    @property
    def children(self) -> typing.Generator[typing.Self, None, None]:
        yield from self.search()


class EntryChain(Entry):
    """EntryChain
    ==================================================
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._entries: typing.List[Entry] = [
            (as_entry(v, **kwargs) if not isinstance(v, Entry) else v)
            for v in args
            if v is not _not_found_ and v is not _undefined_ and v is not None
        ]

    def __copy__(self) -> typing.Self:
        other = super().__copy__()
        other._entries = copy(self._entries)
        return other

    def __str__(self) -> str:
        return ",".join([str(e) for e in self._entries if e._cache is None])

    @property
    def empty(self) -> bool:
        return len(self._entries) == 0

    def find(self, *args, default_value=_not_found_, **kwargs):
        res = super().find(*args, default_value=_not_found_, **kwargs)
        if res is not _not_found_:
            return res

        if len(args) > 0 and args[0] is Query.count:
            # res = super().find(*args, default_value=_not_found_, **kwargs)
            for e in self._entries:
                res = e.child(self._path).find(*args, default_value=_not_found_, **kwargs)
                if res is not _not_found_ and res != 0:
                    break
        else:
            # res = super().find(*args, default_value=_not_found_, **kwargs)
            for e in self._entries:
                e_child = e.child(self._path)
                res = e_child.find(*args, default_value=_not_found_, **kwargs)
                if res is not _not_found_:
                    break

        if res is _not_found_:
            res = default_value

        return res

    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """逐个遍历子节点，不判断重复 id

        Returns:
            typing.Generator[typing.Tuple[int, typing.Any], None, None]: _description_

        Yields:
            Iterator[typing.Generator[typing.Tuple[int, typing.Any], None, None]]: _description_
        """
        if self._cache is not _not_found_:
            yield from super().search(*args, **kwargs)

        for root_entry in self._entries:
            yield from root_entry.child(self._path).search(*args, **kwargs)

            # 根据第一个有效 entry 中的序号，在其他 entry 中的检索子节点

            # if not _entry.exists:
            #     continue
            # for k, e in _entry.for_each(*args, **kwargs):
            # 根据子节点的序号，在其他 entry 中的检索子节点
            # entry_list = [e]
            # for o in self._entrys[idx + 1 :]:
            #     t = o.child(k)
            #     if t.exists:
            #         entry_list.append(t)
            # yield k, ChainEntry(*entry_list)

    @property
    def exists(self) -> bool:
        res = [super().find(Query.exists)]
        res.extend([e.child(self._path).find(Query.exists) for e in self._entries])
        return any(res)


def open_entry(uri: str | URITuple | Path | pathlib.Path, *args, _plugin_name=None, **kwargs):
    """open entry from uri"""

    uri = uri_split(uri)

    fragment = uri.fragment

    uri.fragment = ""

    if _plugin_name is None:
        _plugin_name = uri.protocol

    entry = None
    # FIXME: 注册更多的默认file类型
    if _plugin_name.startswith("file+") or _plugin_name in ("file", "mdsplus", "hdf5", "netcdf", "json", "yaml"):
        from spdm.core.file import File

        if not uri.path:
            entry = Entry()
        else:
            entry = File(uri, *args, kind=_plugin_name, **kwargs).__entry__()

    elif _plugin_name.startswith("service+") or _plugin_name in (
        "service",
        "http",
        "https",
        "ssh",
        "db",
        "mongodb",
        "postgresql",
        "mysql",
        "sqlite",
    ):
        from spdm.core.service import Service

        entry = Service(uri, *args, _plugin_name=_plugin_name, **kwargs).__entry__()
    else:
        from spdm.core.mapper import Mapper

        try:
            entry = Mapper(uri, *args, _plugin_name=_plugin_name, **kwargs)
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(f"{uri.protocol} is not a mapping!") from error

    return entry if not fragment else entry.child(fragment)


@singledispatch
def as_entry(obj, **kwargs) -> Entry:
    """Try convert obj to Entry."""

    if hasattr(obj.__class__, "__entry__"):
        if len(kwargs) > 0:
            logger.warning(f"Unused kwargs   {kwargs}")
        entry = obj.__entry__()
    elif obj is not None and obj is not _not_found_:
        entry = Entry(obj, **kwargs)
    else:
        entry = Entry(**kwargs)

    return entry


@as_entry.register(Entry)
def _as_entry(obj, **kwargs):
    if len(kwargs) > 0:
        raise RuntimeError(f"Unused arguments  {kwargs}")
    return obj


@as_entry.register(str)
def _as_entry(uri, **kwargs):
    return open_entry(uri, **kwargs)


@as_entry.register(URITuple)
def _as_entry(uri, **kwargs):
    return open_entry(uri, **kwargs)


@as_entry.register(Path)
def _as_entry(uri, **kwargs):
    return open_entry(uri, **kwargs)


@as_entry.register(pathlib.Path)
def _as_entry(uri, *args, **kwargs):
    return open_entry(uri, **kwargs)


def _as_entrychain(uris, **kwargs):
    entries = []
    for uri in uris:
        if uri is None or uri is _not_found_:
            continue
        elif isinstance(uri, EntryChain):
            entries.extend([e.child(uri._path) for e in uri._entries])
        elif isinstance(uri, (list, tuple)):
            entries.extend(uri)
        else:
            entries.append(uri)

    if len(entries) == 0:
        return None
    elif len(entries) == 1:
        return as_entry(entries[0], **kwargs)
    else:
        return EntryChain(*entries, **kwargs)


@as_entry.register(list)
def _as_entry(uris, **kwargs):
    return _as_entrychain(uris, **kwargs)


@as_entry.register(tuple)
def _as_entry(uris, **kwargs):
    return _as_entrychain(uris, **kwargs)
