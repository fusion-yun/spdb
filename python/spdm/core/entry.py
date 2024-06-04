from __future__ import annotations
import numpy as np
import collections
import collections.abc
import dataclasses
import inspect
import os
import pathlib
import typing
from copy import copy, deepcopy

from ..utils.logger import deprecated, logger
from ..utils.plugin import Pluggable
from ..utils.tags import _not_found_, _undefined_
from ..utils.typing import array_type, as_array, as_value, is_scalar
from ..utils.uri_utils import URITuple, uri_split, uri_split_as_dict
from .path import Path, PathLike, as_path, update_tree, update_tree

PROTOCOL_LIST = ["local", "file", "http", "https", "ssh", "mdsplus"]


class Entry(Pluggable):
    _plugin_prefix = "spdm.plugins.data.plugin_"
    _plugin_registry = {}

    def __init__(
        self,
        data: typing.Any = _not_found_,
        path: Path | PathLike = [],
        *args,
        scheme=None,
        **kwargs,
    ):
        if self.__class__ is not Entry:
            pass
        elif scheme is not None or isinstance(data, (str, URITuple, pathlib.Path)):
            if scheme is None:
                scheme = uri_split(data).protocol

            if isinstance(scheme, str) and scheme != "":
                super().__dispatch_init__([scheme, EntryProxy], self, data, *args, **kwargs)
                return

        self._data = data
        self._path = as_path(path)

    def __copy__(self) -> typing.Self:
        other = object.__new__(self.__class__)
        other._data = self._data
        other._path = deepcopy(self._path)
        return other

    def reset(self, value=None, path=None) -> Entry:
        self._data = value
        self._path = as_path(path)
        return self

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} path="{self._path}" />'

    def __repr__(self) -> str:
        return str(self._path)

    @property
    def __entry__(self) -> Entry:
        return self

    @property
    def is_writable(self) -> bool:
        return False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_leaf(self) -> bool:
        return self.find(Path.tags.is_leaf)

    @property
    def is_list(self) -> bool:
        return self.find(Path.tags.is_list)

    @property
    def is_dict(self) -> bool:
        return self.find(Path.tags.is_dict)

    @property
    def is_root(self) -> bool:
        return len(self._path) == 0

    @property
    def is_generator(self) -> bool:
        return self._path.is_generator

    ###########################################################

    @property
    def _value_(self) -> typing.Any:
        return self._data if len(self._path) == 0 else self.get(default_value=_not_found_)

    def __getitem__(self, *args) -> Entry:
        return self.child(*args)

    def __setitem__(self, path, value):
        return self.child(path).update(value)

    def __delitem__(self, *args):
        return self.child(*args).remove()

    def get(self, query=None, default_value=_not_found_, **kwargs) -> typing.Any:
        if query is None:
            entry = self
            args = ()
        elif isinstance(query, (slice, set, dict)):
            entry = self
            args = (query,)
        else:
            entry = self.child(query)
            args = ()

        return entry.find(Path.tags.find, *args, default_value=default_value, **kwargs)

    def put(self, pth, value, *args, **kwrags) -> Entry:
        entry = self.child(pth)
        entry.update(value, *args, **kwrags)
        return entry

    def dump(self, *args, **kwargs) -> typing.Any:
        return self.find(Path.tags.dump, *args, **kwargs)

    def equal(self, other) -> bool:
        if isinstance(other, Entry):
            return self.find(Path.tags.equal, other.__value__)
        else:
            return self.find(Path.tags.equal, other)

    @property
    def count(self) -> int:
        return self.find(Path.tags.count)

    @property
    def exists(self) -> bool:
        return self.find(Path.tags.exists)

    def check_type(self, tp: typing.Type) -> bool:
        return self.find(Path.tags.check_type, tp)

    ###########################################################

    @property
    def root(self) -> Entry:
        other = copy(self)
        other._path = []
        return other

    @property
    def parent(self) -> Entry:
        other = copy(self)
        other._path = self._path.parent
        return other

    def child(self, path=None, *args, **kwargs) -> Entry:
        path = as_path(path)
        if len(path) == 0:
            return self

        if self._data is not None or len(self._path) == 0:
            pass
        elif isinstance(self._path[0], str):
            self._data = {}
        else:
            self._data = []

        other = self.__copy__()
        other._path.append(path)
        return other

    def next(self, inc: int = 1) -> Entry:
        if not isinstance(self._path[-1], int) and not np.issubdtype(type(self._path[-1]), np.integer):
            raise RuntimeError(f"Path must be end with int! {self._path[-1]} {type(self._path[-1])}")

        next_ = self.__copy__()

        next_._path[-1] += inc

        return next_

    ###########################################################
    # API: CRUD  operation

    def insert(self, value, *args, **kwargs) -> Entry:
        self._data, *others = self._path.insert(self._data, value, *args, **kwargs)
        return self.__class__(self._data, *others)

    def update(self, value, *args, **kwargs) -> Entry:
        self._data = self._path.update(self._data, value, *args, **kwargs)
        return self

    def remove(self, *args, **kwargs) -> int:
        self._data, num = self._path.remove(self._data, *args, **kwargs)
        return num

    def find(self, *args, **kwargs) -> typing.Any:
        """
        Query the Entry.
        Same function as `find`, but put result into a contianer.
        Could be overridden by subclasses.
        """
        return self._path.find(self._data, *args, **kwargs)

    def keys(self) -> typing.Generator[str, None, None]:
        yield from self._path.keys(self._data)

    def for_each(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """Return a generator of the results."""
        yield from self._path.for_each(self._data, *args, **kwargs)

    def search(self, *args, **kwargs) -> Entry:
        raise NotImplementedError()

    ###########################################################


class ChainEntry(Entry):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._entrys: typing.List[Entry] = [
            (_open_entry(v, **kwargs) if not isinstance(v, Entry) else v)
            for v in args
            if v is not _not_found_ and v is not _undefined_ and v is not None
        ]

    def __copy__(self) -> ChainEntry:
        other = super().__copy__()
        other._entrys = self._entrys
        return other

    def __str__(self) -> str:
        return ",".join([str(e) for e in self._entrys if e._data is None])

    @property
    def is_writable(self) -> bool:
        return self._entrys[0].is_writable

    def find(self, *args, default_value=_not_found_, **kwargs):
        if len(args) > 0 and args[0] is Path.tags.count:
            res = super().find(*args, default_value=_not_found_, **kwargs)
            if res is _not_found_ or res == 0:
                for e in self._entrys:
                    res = e.child(self._path).find(*args, default_value=_not_found_, **kwargs)
                    if res is not _not_found_ and res != 0:
                        break
        else:
            res = super().find(*args, default_value=_not_found_, **kwargs)

            if res is _not_found_:
                for e in self._entrys:
                    e_child = e.child(self._path)
                    res = e_child.find(*args, default_value=_not_found_, **kwargs)
                    if res is not _not_found_:
                        break

            if res is _not_found_:
                res = default_value

        return res

    def for_each(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int, typing.Any], None, None]:
        """逐个遍历子节点，不判断重复 id

        Returns:
            typing.Generator[typing.Tuple[int, typing.Any], None, None]: _description_

        Yields:
            Iterator[typing.Generator[typing.Tuple[int, typing.Any], None, None]]: _description_
        """

        for root_entry in self._entrys:
            yield from root_entry.child(self._path).for_each(*args, **kwargs)

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

    def search(self, *args, **kwargs):
        return ChainEntry(*[e.search(*args, **kwargs) for e in self._entrys])

    @property
    def exists(self) -> bool:
        res = [super().find(Path.tags.exists)]
        res.extend([e.child(self._path).find(Path.tags.exists) for e in self._entrys])
        return any(res)


def _open_entry(entry: str | URITuple | pathlib.Path | Entry, mapping_files=None, local_schema=None, **kwargs) -> Entry:
    """
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
    if isinstance(entry, (dict, list)):
        # 如果是一个字典或者列表，直接转换成 Entry
        return Entry(entry)

    elif isinstance(entry, Entry):
        # 如果是一个Entry，直接返回
        if len(kwargs) > 0:  # pragma: no cover
            logger.warning(f"ignore {kwargs}")
        return entry

    elif isinstance(entry, str):
        # 如果是一个字符串，需要进行解析
        uri = uri_split(entry)

    elif isinstance(entry, pathlib.Path):
        # 如果是一个pathlib.Path，需要转换
        uri = URITuple(protocol="file", fragment=kwargs.pop("fragment", ""), query=kwargs, path=entry)

    elif isinstance(entry, URITuple):
        # 如果是一个URITuple，不需要转换
        uri = entry

    else:
        # 其他类型，报错
        raise RuntimeError(f"Unknown entry {entry} {type(entry)}")

    # if not isinstance(uri.path, str):
    #     raise RuntimeError(f"{entry} {uri}")

    fragment = uri.fragment

    query = update_tree(uri.query, kwargs)

    global_schema = query.pop("global_schema", None)

    schemas = [s for s in uri.protocol.split("+") if s != ""]

    local_schema = local_schema or query.pop("local_schema", None) or query.pop("device", None)
    if len(schemas) > 0 and schemas[0] not in PROTOCOL_LIST:
        local_schema = schemas[0]
        schemas = schemas[1:]

    new_url = URITuple(
        protocol="+".join(schemas),
        authority=uri.authority,
        path=uri.path,
        query=query,
        fragment="",
    )

    if new_url.protocol.startswith(("local+", "file+")):  # or (new_url.protocol == "" and new_url.path != ""):
        # 单一文件不进行 schema 检查，直接读取。因为schema转换在文件plugin中进行。
        from .file import File

        entry = File(new_url, **query).read()
    elif new_url.protocol.startswith(("http", "https", "ssh")):
        # http/https/ssh 协议，不进行schema检查，直接读取
        raise NotImplementedError(f"{new_url}")
    elif local_schema is not None and global_schema != local_schema:
        # 本地schema和全局schema不一致，需要进行schema转换
        entry = EntryProxy(new_url, local_schema=local_schema, global_schema=global_schema, **query)
    else:
        entry = Entry(new_url, **query)

    if fragment:
        entry = entry.child(fragment.replace(".", "/"))

    return entry


def open_entry(entry, local_schema=None, **kwargs) -> Entry:
    if (entry is None or isinstance(entry, Entry)) and local_schema is None:
        if len(kwargs) > 0:
            logger.warning(f"ignore {kwargs}")
        return entry
    elif isinstance(entry, list) and len(entry) == 1 and isinstance(entry[0], Entry):
        return entry[0]

    if entry is None or entry is _not_found_ or (isinstance(entry, list) and len(entry) == 0):
        if local_schema is None:
            return None
        else:
            entry = [f"{local_schema}://"]
    if not isinstance(entry, list):
        entry = [entry]

    entry = [a for a in entry if a is not None and a is not _not_found_]

    if isinstance(local_schema, str) and not any(
        [e.startswith(f"{local_schema}+") or e.startswith(f"mdsplus://") for e in entry if isinstance(e, str)]
    ):
        # just a walk around for mdsplus://
        entry = [f"{local_schema}://"] + entry

    if len(entry) == 0:
        return None

    elif len(entry) > 1:
        return ChainEntry(*entry, local_schema=local_schema, **kwargs)

    else:
        return _open_entry(entry[0], local_schema=local_schema, **kwargs)

    # url = uri_split(url_s)

    # # scheme = url.protocol.split("+")

    # # local_schema = None

    # # global_schema = schema

    # # match len(scheme):
    # #     case 0:
    # #         url.protocol = 'local'
    # #     case 1:
    # #         if scheme[0] not in _predefined_protocols:
    # #             local_schema = scheme[0]
    # #             url.protocol = ""
    # #     case _:
    # #         if scheme[0] in _predefined_protocols:
    # #             url.protocol = scheme[0]
    # #             if scheme[1] != kwargs.setdefault("format", scheme[1]):
    # #                 raise ValueError(f"Format mismatch! {scheme[1]} != {kwargs['format']}")
    # #         else:
    # #             local_schema = scheme[0]
    # #             url.protocol = "+".join(scheme[1:])

    # # if local_schema is not None:
    # #     kwargs.update(url.query)
    # #     if url.authority != '' or url.path != '':
    # #         kwargs['netloc'] = url.authority
    # #         kwargs['path'] = url.path
    # #     return EntryProxy(local_schema=local_schema, global_schema=global_schema, ** kwargs)

    # if url.protocol in ["file", "local", "", None]:
    #     from .file import File
    #     return File(url, *args, **kwargs).read()

    # elif url.protocol in ["https", "http"]:
    #     return Entry(url, *args, **kwargs)

    # else:
    #     raise RuntimeError(f"Unknown url {url} {Entry._plugin_registry}")


def as_entry(obj, *args, **kwargs) -> Entry:
    if isinstance(obj, Entry):
        entry = obj
    elif isinstance(obj, (str, URITuple, pathlib.Path)):
        entry = open_entry(obj, *args, **kwargs)
    elif hasattr(obj.__class__, "__entry__"):
        entry = obj.__entry__
    elif obj is None or obj is _not_found_:
        entry = Entry()
    else:
        entry = Entry(obj, *args, **kwargs)

    return entry


def as_dataclass(dclass, obj, default_value=None):
    if dclass is dataclasses._MISSING_TYPE:
        return obj

    if hasattr(obj, "entry"):
        obj = obj.entry
    if obj is None:
        obj = default_value

    if obj is None or not dataclasses.is_dataclass(dclass) or isinstance(obj, dclass):
        pass
    # elif getattr(obj, 'empty', False):
    #   obj = None
    elif dclass is array_type:
        obj = as_array(obj)
    elif hasattr(obj.__class__, "get"):
        obj = dclass(
            **{
                f.name: as_dataclass(
                    f.type,
                    obj.get(
                        f.name,
                        f.default if f.default is not dataclasses.MISSING else None,
                    ),
                )
                for f in dataclasses.fields(dclass)
            }
        )
    elif isinstance(obj, collections.abc.Sequence):
        obj = dclass(*obj)
    else:
        try:
            obj = dclass(obj)
        except Exception as error:
            logger.debug((type(obj), dclass))
            raise error
    return obj


def deep_reduce(first=None, *others, level=-1):
    if level == 0 or len(others) == 0:
        return first if first is not _not_found_ else None
    elif first is None or first is _not_found_:
        return deep_reduce(others, level=level)
    elif isinstance(first, str) or is_scalar(first):
        return first
    elif isinstance(first, array_type):
        return sum([first, *(v for v in others if (v is not None and v is not _not_found_))])
    elif len(others) > 1:
        return deep_reduce(first, deep_reduce(others, level=level), level=level)
    elif others[0] is None or first is _not_found_:
        return first
    elif isinstance(first, collections.abc.Sequence):
        if isinstance(others[0], collections.abc.Sequence) and not isinstance(others, str):
            return [*first, *others[0]]
        else:
            return [*first, others[0]]
    elif isinstance(first, collections.abc.Mapping) and isinstance(others[0], collections.abc.Mapping):
        second = others[0]
        res = {}
        for k, v in first.items():
            res[k] = deep_reduce(v, second.get(k, None), level=level - 1)
        for k, v in second.items():
            if k not in res:
                res[k] = v
        return res
    elif others[0] is None or others[0] is _not_found_:
        return first
    else:
        raise TypeError(f"Can not merge dict with {others}!")


def convert_fromentry(cls, obj, *args, **kwargs):
    origin_type = getattr(cls, "__origin__", cls)
    if dataclasses.is_dataclass(origin_type):
        obj = as_dataclass(origin_type, obj)
    elif inspect.isclass(origin_type):
        obj = cls(obj, *args, **kwargs)
    elif callable(cls) is not None:
        obj = cls(obj, *args, **kwargs)

    return obj


SPDB_XML_NAMESPACE = "{http://fusionyun.org/schema/}"

SPDB_TAG = "spdb"
########################################################
#  mapping files 目录结构约定为 :
#         ```{text}
#         - <local schema>/<global schema>
#              config.xml
#             - static            # 存储静态数据，例如装置描述文件
#                 - config.xml
#                 - <...>

#             - protocol0         # 存储 protocol0 所对应mapping，例如 mdsplus
#                 - config.xml
#                 - <...>

#             - protocol1         # 存储 protocol1 所对应mapping，例如 hdf5
#                 - config.xml
#                 - <...>
#         ```
#         Example:   east+mdsplus://.... 对应的目录结构为
#         ```{text}
#         - east/imas/3
#             - static
#                 - config.xml
#                 - wall.xml
#                 - pf_active.xml  (包含 pf 线圈几何信息)
#                 - ...
#             - mdsplus
#                 - config.xml (包含<spdb > 描述子数据库entry )
#                 - pf_active.xml
#         ```


class EntryProxy(Entry):
    _maps = {}
    _mapping_path = []
    _default_local_schema: str = "EAST"
    _default_global_schema: str = "imas/3"

    @classmethod
    def load(
        cls,
        url: str | None = None,
        local_schema: str = None,
        global_schema: str = None,
        mapping_files=None,
        **kwargs,
    ):
        """检索并导入 mapping files"""
        from .file import File

        if len(EntryProxy._mapping_path) == 0:
            EntryProxy._mapping_path.extend(
                [pathlib.Path(p) for p in os.environ.get("SP_DATA_MAPPING_PATH", "").split(":") if p != ""]
            )

        mapper_list = EntryProxy._maps

        _url = uri_split(url)

        kwargs = update_tree(url.query, kwargs)

        enabled_entry = kwargs.pop("enable", "").split(",")

        if local_schema is None:
            local_schema = EntryProxy._default_local_schema

        if global_schema is None:
            global_schema = EntryProxy._default_global_schema

        map_tag = [local_schema.lower(), global_schema.lower()]

        if _url.protocol != "":
            map_tag.append(_url.protocol)

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

            if mapping_files is None:
                mapping_files: typing.List[pathlib.Path] = []

            for m_dir in EntryProxy._mapping_path:
                if not m_dir:
                    continue
                elif isinstance(m_dir, str):
                    m_dir = pathlib.Path(m_dir)

                for file_name in config_files:
                    p = m_dir / file_name
                    if p.exists():
                        mapping_files.append(p)

            if len(mapping_files) == 0:
                raise FileNotFoundError(
                    f"Can not find mapping files for {map_tag} MAPPING_PATH={EntryProxy._mapping_path} !"
                )

            mapper = File(mapping_files, mode="r", format="XML").read()

            mapper_list[map_tag_str] = mapper

        entry_list = {}

        spdb = mapper.child("spdb").find()

        if not isinstance(spdb, dict):
            entry_list["*"] = _url
        else:
            attr = {k[1:]: v for k, v in spdb.items() if k.startswith("@")}

            attr["prefix"] = f"{_url.protocol}://{_url.authority}{_url.path}"

            attr.update(kwargs)

            for entry in spdb.get("entry", []):
                id = entry.get("@id", None)

                enable = entry.get("@enable", "true") == "true"

                if id is None:
                    continue
                elif not enable and id not in enabled_entry:
                    continue

                entry_list[id] = entry.get("_text", "").format(**attr)

        return mapper, entry_list

    def __init__(self, *args, **kwargs):
        super().__init__()
        if len(args) == 2 and isinstance(args[0], Entry) and isinstance(args[1], dict):
            self._mapper = args[0]
            self._entry_list = args[1]
        else:
            self._mapper, self._entry_list = self.__class__.load(*args, **kwargs)

    def __copy__(self) -> typing.Self:
        other = super().__copy__()
        other._mapper = self._mapper
        other._entry_list = self._entry_list
        return other

    def __str__(self) -> str:
        return ",".join([str(e) for e in self._entry_list.values() if isinstance(e, str)])

    def child(self, *args, **kwargs) -> typing.Self:
        res: EntryProxy = super().child(*args, **kwargs)
        res._entry_list = self._entry_list
        return res

    def insert(self, value, **kwargs) -> typing.Self:
        raise NotImplementedError(f"")

    def update(self, value, **kwargs) -> typing.Self:
        raise NotImplementedError(f"")

    def remove(self, **kwargs) -> int:
        raise NotImplementedError(f"")

    def find(self, *args, default_value=_not_found_, **kwargs) -> typing.Any:
        request = self._mapper.child(self._path).find(*args, default_value=_not_found_, lazy=False, **kwargs)

        return self._op_find(request, default_value=default_value)

    def for_each(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int, typing.Any], None, None]:
        """Return a generator of the results."""
        for idx, request in self._mapper.child(self._path).for_each(*args, **kwargs):
            yield idx, self._op_find(request)

    def search(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_entry_by_name(self, entry_name: str, default_value=None) -> Entry | None:
        entry = self._entry_list.get(entry_name, None)

        if isinstance(entry, (str, URITuple)):
            entry = open_entry(entry)
            self._entry_list[entry_name] = entry

        if isinstance(entry, Entry):
            pass
        elif default_value is _not_found_:
            raise RuntimeError(f"Can not find entry for {entry_name}")
        else:
            entry = default_value

        return entry

    def _op_find(self, request: typing.Any, *args, **kwargs) -> typing.Any:
        # if isinstance(request, str) and "://" in request:
        #     request = uri_split_as_dict(request)

        if request is _not_found_ or request is None:
            defaultentry = self._get_entry_by_name("*", None)
            if defaultentry is None:
                res = _not_found_
            else:
                res = defaultentry.child(self._path).find(None, *args, **kwargs)

        elif isinstance(request, Entry):
            res = EntryProxy(request, self._entry_list)

        elif isinstance(request, list):
            res = [self._op_find(req, *args, **kwargs) for req in request]

        elif not isinstance(request, dict):
            res = request

        elif "@spdb" not in request:
            res = {k: self._op_find(req, *args, **kwargs) for k, req in request.items()}

        else:
            entry = self._get_entry_by_name(request.get("@spdb", None))

            if not isinstance(entry, Entry):
                raise RuntimeError(f"Can not find entry for {request}")

            res = entry.find(request.get("_text"), *args, **kwargs)

        return res
