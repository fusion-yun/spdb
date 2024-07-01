from __future__ import annotations

import pathlib
import typing
from copy import copy
import os
from functools import singledispatch

from spdm.utils.tags import _not_found_, _undefined_
from spdm.utils.uri_utils import URITuple, uri_split
from spdm.core.pluggable import Pluggable
from spdm.core.path import Path, as_path, Query

from spdm.utils.logger import logger


class Entry(Pluggable):  # pylint: disable=R0904
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

    _plugin_prefix = "spdm.plugins.data."

    _plugin_registry = {}

    def __new__(cls, *args, _plugin_name=None, **kwargs):
        if _plugin_name is None:
            return super().__new__(cls)
        else:
            return super().__new__(cls, *args, _plugin_name=_plugin_name, **kwargs)

    def __init__(self, *args, **kwargs):
        self._cache = _not_found_ if len(args) == 0 else args[0]
        self._path = as_path(*args[1:], **kwargs)

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

    def insert(self, value, *args, **kwargs) -> typing.Self:
        return self.child(Path.tags.append).update(value, *args, **kwargs)

    def update(self, value, *args, **kwargs) -> typing.Self:
        self._cache = self._path.update(self._cache, value, *args, **kwargs)
        return self

    def delete(self, *args, **kwargs) -> bool:
        return self._path.delete(self._cache, *args, **kwargs)

    def find(self, *args, **kwargs) -> typing.Any:
        """find the first result."""
        return self._path.find(self._cache, *args, **kwargs)

    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """search all the results."""
        yield from self._path.search(self._cache, *args, **kwargs)

    # -----------------------------------------------------------
    # alias

    def query(self, *args, **kwargs) -> typing.Any:
        """alias of find"""
        return self.find(*args, **kwargs)

    def keys(self) -> typing.Generator[str, None, None]:
        yield from self.search(Query.tags.get_key)

    def values(self) -> typing.Generator[str, None, None]:
        yield from self.search(Query.tags.get_value)

    def for_each(self) -> typing.Generator[typing.Any, None, None]:
        """alis of search"""
        yield from self.search()

    def __setitem__(self, key, value) -> None:
        return self.put(key, value)

    def __getitem__(self, key) -> typing.Self:
        return self.child(key)

    def get(self, path=None, default_value=_not_found_) -> typing.Any:
        return self.child(path).find(default_value=default_value)

    def put(self, *args, **kwargs) -> None:
        return self.child(*args[:-1]).update(*args[-1:], **kwargs)

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
    def children(self) -> typing.Generator[typing.Type[Entry], None, None]:
        yield self.search()


class EntryChain(Entry):
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

    def find(self, *args, default_value=_not_found_, **kwargs):
        res = super().find(*args, default_value=_not_found_, **kwargs)
        if res is not _not_found_:
            return res

        if len(args) > 0 and args[0] is Query.count:
            res = super().find(*args, default_value=_not_found_, **kwargs)
            if res is _not_found_ or res == 0:
                for e in self._entries:
                    res = e.child(self._path).find(*args, default_value=_not_found_, **kwargs)
                    if res is not _not_found_ and res != 0:
                        break
        else:
            res = super().find(*args, default_value=_not_found_, **kwargs)

            if res is _not_found_:
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


class EntryBundle(Entry):
    """Entry Bundle, 用于管理多个 Entry"""

    def __init__(self, *args, **kwargs: typing.Tuple[str, Entry]):
        super().__init__(*args)
        self._bundle = {
            k: as_entry(v)
            for k, v in kwargs.items()
            if not k.startswith("_") and v is not None and v is not _not_found_
        }

    def __copy__(self) -> typing.Self:
        other = super().__copy__()
        other._bundle = self._bundle
        return other

    def _dispatch(self, *args, **kwargs) -> Entry:
        entry_name = "_"
        entry = self._bundle.get(entry_name, None)

        # if isinstance(entry, (str, URITuple)):
        #     entry = open_entry(entry)
        #     self._bundle[entry_name] = entry
        # # if isinstance(entry, Entry):
        # #     pass
        # # elif default_value is _not_found_:
        # #     raise RuntimeError(f"Can not find entry for {entry_name}")
        # # else:
        # #     entry = default_value
        if entry is None:
            return Entry()
        else:
            return entry.child(self._path)
            # raise RuntimeError(f"Can not find  {entry_name}")

    def insert(self, *args, **kwargs) -> typing.Self:
        return self._dispatch(*args, **kwargs).insert(*args, **kwargs)

    def update(self, *args, **kwargs) -> typing.Self:
        return self._dispatch(*args, **kwargs).update(*args, **kwargs)

    def delete(self, *args, **kwargs) -> int:
        return self._dispatch(*args, **kwargs).delete(*args, **kwargs)

    def find(self, *args, **kwargs) -> typing.Any:
        return self._dispatch(*args, **kwargs).find(*args, **kwargs)

    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        yield from self._dispatch(*args[:1]).search(*args[1:], **kwargs)


class EntryMapping(EntryBundle, plugin_name="mapping"):

    def __init__(self, uri, /, local_schema=None, global_schema=None, **kwargs):

        if local_schema is None:
            uri = uri_split(uri)
            schemas = uri.protocol.split("+")
            local_schema = schemas[0]
            uri.protocol = "+".join(schemas[1:])

        mapper, other_entries = _load_mapper(local_schema=local_schema, global_schema=global_schema)

        super().__init__(**other_entries, **kwargs)

        self._bundle["*"] = as_entry(uri)

        self._mapper = mapper

    def __copy__(self) -> typing.Self:
        other = super().__copy__()
        other._mapper = self._mapper
        return other

    def _do_map(self, req):
        if not isinstance(req, dict):
            return req

        if "@spdb" not in req:
            return {k: self._do_map(v) for k, v in req.items()}

        entry = self._dispatch(req.get("@spdb", None))

        if not isinstance(entry, Entry):
            raise RuntimeError(f"Can not find entry for {req}")

        return entry.find(req.get("_text"))

    def _map(self, *args) -> Entry:
        res = self._mapper.child(self._path).get(*args, _not_found_)
        return Entry(self._do_map(res))

    def insert(self, *args, **kwargs) -> typing.Self:
        return self._map(*args[:-1]).insert(*args[-1:], **kwargs)

    def update(self, *args, **kwargs) -> typing.Self:
        return self._map(*args[:-1]).update(*args[-1:], **kwargs)

    def delete(self, *args, **kwargs) -> int:
        return self._map(*args[:1]).delete(*args[1:], **kwargs)

    def find(self, *args, **kwargs) -> typing.Any:
        return self._map(*args[:1]).find(*args[1:], **kwargs)

    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """Return a generator of the results."""
        yield from self._map(*args[:1]).search(*args[1:], **kwargs)


mapping_path = [pathlib.Path(p) for p in os.environ.get("SP_DATA_MAPPING_PATH", "").split(":") if p != ""]

_maps = {}

_default_local_schema: str = "EAST"
_default_global_schema: str = "imas/3"


def _load_mapper(local_schema: str, global_schema: str = None) -> typing.Tuple[Entry, typing.Dict[str, Entry]]:
    """
    mapping files 目录结构约定为 :
        ```{text}
        - <local schema>/<global schema>
                config.xml
            - static            # 存储静态数据，例如装置描述文件
                - config.xml
                - <...>
            - protocol0         # 存储 protocol0 所对应mapping，例如 mdsplus
                - config.xml
                - <...>
            - protocol1         # 存储 protocol1 所对应mapping，例如 hdf5
                - config.xml
                - <...>
        ```
        Example:   east+mdsplus://.... 对应的目录结构为
        ```{text}
        - east/imas/3
            - static
                - config.xml
                - wall.xml
                - pf_active.xml  (包含 pf 线圈几何信息)
                - ...
            - mdsplus
                - config.xml (包含<spdb > 描述子数据库entry )
                - pf_active.xml
        ```
    """

    mapping_files = []

    mapper_list = _maps

    if local_schema is None:
        local_schema = _default_local_schema

    if global_schema is None:
        global_schema = _default_global_schema

    map_tag = [local_schema.lower(), global_schema.lower()]

    map_tag_str = "/".join(map_tag)

    mapper = mapper_list.get(map_tag_str, _not_found_)

    if mapper is _not_found_:
        prefix = "/".join(map_tag[:2])

        config_files = [
            f"{prefix}/config.xml",
            f"{prefix}/static/config.xml",
            f"{prefix}/{local_schema.lower()}.xml",
        ]

        if len(map_tag) > 2:
            config_files.append(f"{'/'.join(map_tag[:3])}/config.xml")

        for m_dir in mapping_path:
            if not m_dir:
                continue

            if isinstance(m_dir, str):
                m_dir = pathlib.Path(m_dir)

            for file_name in config_files:
                p = m_dir / file_name
                if p.exists():
                    mapping_files.append(p)

        if len(mapping_files) == 0:
            raise FileNotFoundError(
                f"Can not find mapping files for {map_tag} MAPPING_PATH={mapping_path}  {mapping_files}!"
            )

        mapper = open_entry(mapping_files, mode="r", plugin_name="file+xml")

        mapper_list[map_tag_str] = mapper

    entry_list = {}

    # spdb = mapper.child("spdb").get()
    # if not isinstance(spdb, dict):
    #     entry_list["*"] = _url
    # else:
    #     attr = {k[1:]: v for k, v in spdb.items() if k.startswith("@")}
    #     attr["prefix"] = f"{_url.protocol}://{_url.authority}{_url.path}"
    #     attr.update(kwargs)
    #     for entry in spdb.get("entry", []):
    #         nid = entry.get("@id", None)
    #         enable = entry.get("@enable", "true") == "true"
    #         if nid is None:
    #             continue
    #         elif not enable and nid not in enabled_entry:
    #             continue
    #         entry_list[id] = entry.get("_text", "").format(**attr)

    return mapper, entry_list


def open_entry(uri: str | URITuple | Path | pathlib.Path, *args, plugin_name: str = None, local_schema=None, **kwargs):
    """open entry from uri"""

    uri = uri_split(uri)

    if plugin_name is None:
        plugin_name = uri.protocol

    if local_schema is not None:
        return EntryMapping(uri, *args, local_schema=local_schema, **kwargs)

    if plugin_name.startswith("file") or plugin_name == "":
        from spdm.core.file import File

        return File(uri, *args, _plugin_name=plugin_name, **kwargs).entry

    fragment = uri.fragment

    uri.fragment = ""

    plugin_name = uri.protocol

    schemas = plugin_name.split("+")

    entry = None

    for pos in range(len(schemas), 0, -1):
        plugin_name = "+".join(schemas[:pos])
        plugin = Entry._find_plugin(plugin_name)  # pylint: disable=w0212

        if plugin is not None:
            sub_uri = copy(uri)
            sub_uri.protocol = "+".join(schemas[pos:])
            if sub_uri.protocol == "":
                sub_uri.protocol = "file"

            entry = plugin(sub_uri, *args, _plugin_name=plugin_name, **kwargs)
            break
    else:
        try:
            uri.protocol = "+".join(schemas[1:])
            entry = EntryMapping(uri, *args, local_schema=schemas[0], **kwargs)
        except RuntimeError as error:
            raise RuntimeError(f"Can not find plugin for {uri}") from error

    return entry if len(fragment) == 0 else entry.child(fragment)


@singledispatch
def as_entry(obj, *args, plugin_name=None, **kwargs) -> Entry:
    """Try convert obj to Entry."""

    if plugin_name is not None:
        entry = Entry(obj, *args, _plugin_name=plugin_name, **kwargs)
    elif hasattr(obj.__class__, "__entry__"):
        if len(args) + len(kwargs) > 0:
            raise RuntimeError(f"Unused arguments {args} {kwargs}")
        entry = obj.__entry__()
    else:
        entry = Entry(obj, *args, **kwargs)

    return entry


@as_entry.register(Entry)
def _as_entry(obj, *args, **kwargs):
    if len(args) + len(kwargs) == 0:
        raise RuntimeError(f"Unused arguments {args} {kwargs}")
    return obj


@as_entry.register(str)
def _as_entry(uri, *args, **kwargs):
    return open_entry(uri, *args, **kwargs)


@as_entry.register(URITuple)
def _as_entry(uri, *args, **kwargs):
    return open_entry(uri, *args, **kwargs)


@as_entry.register(Path)
def _as_entry(uri, *args, **kwargs):
    return open_entry(uri, *args, **kwargs)


@as_entry.register(pathlib.Path)
def _as_entry(uri, *args, **kwargs):
    return open_entry(uri, *args, **kwargs)
