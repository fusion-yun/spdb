import pathlib
import typing
from importlib import resources
from copy import copy
import os

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.uri_utils import URITuple, uri_split
from spdm.core.entry import Entry, as_entry
from spdm.core.file import File


path = "spdm/mapping/{schema}"


class Mapper(Entry):

    _mappers = {}

    _mapping_path = []

    _default_local_schema: str = "EAST"
    _default_global_schema: str = "imas/3"

    def __init__(self, uri, *args, schema=None, namespace=None, **kwargs):
        super().__init__(*args, **kwargs)

        if schema is None:
            uri: URITuple = uri_split(uri)
            schemas = uri.protocol.split("+")
            schema = schemas[0]
            uri.protocol = "+".join(schemas[1:])
            if uri.protocol == "":
                uri.protocol = "file"
            elif uri.netloc == "" and not uri.protocol.startswith("file"):
                uri.protocol = "file+" + uri.protocol

        self._mapper, self._handler = Mapper._get_mapper(schema, uri, namespace)

    def __copy__(self) -> typing.Self:
        other = super().__copy__()
        other._mapper = self._mapper
        other._handler = self._handler
        return other

    def _do_map(self, req):
        if isinstance(req, dict):
            if "@spdm" not in req:
                res = {k: self._do_map(v) for k, v in req.items()}
            else:
                entry = self._handler.get(req.get("@spdm", None), None)
                if not isinstance(entry, Entry):
                    # raise RuntimeError(f"Can not find entry for {req}")
                    res = _not_found_
                else:
                    res = entry.find(req.get("_text"))
        elif isinstance(req, list) and any(isinstance(i, dict) for i in req):
            res = [self._do_map(i) for i in req]
        elif isinstance(req, tuple):
            k, req = req
            res = (k, self._do_map(req))
        else:
            res = req
        return res

    def _map(self, *args) -> Entry:
        value = self._mapper.child(self._path).find(*args, default_value=_not_found_)
        value = self._do_map(value)
        if value is _not_found_:
            value = self._handler["*"].child(self._path).get(*args, default_value=_not_found_)
        return Entry(value)

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
        for value in self._mapper.child(self._path).search(*args[:1], default_value=_not_found_):
            if value is _not_found_:
                continue

            yield from Entry(value).search(*args[1:], **kwargs)

    @classmethod
    def _get_mapper(cls, schema, uri, namespace=None) -> typing.Tuple[Entry, typing.Dict[str, Entry]]:

        uri = uri_split(uri)

        if namespace is None:
            namespace = path

        namespace: str = namespace.format(schema=schema)

        mapper_tag = (namespace, uri)

        mapper_hash = hash(mapper_tag)

        mapper, handlers = cls._mappers.get(mapper_hash, (_not_found_, _not_found_))

        if mapper is not _not_found_:
            return mapper, handlers

        mapping_paths = []
        for ns in namespace.replace("/", ".").split(":"):
            try:
                files = resources.files(ns)
            except ModuleNotFoundError:
                continue

            if not isinstance(files, pathlib.Path):
                mapping_paths.extend(files._paths)
            else:
                mapping_paths.append(files)

        mapping_files = []

        config_files = [
            "config.xml",
            "static/config.xml",
            # "dynamic/config.xml",
            f"{schema}.xml",
            f"{uri.protocol}.xml",
            f"{uri.protocol}/config.xml",
        ]

        for m_dir in mapping_paths:
            for file_name in config_files:
                p = m_dir / file_name
                if p.exists():
                    mapping_files.append(p)

        if len(mapping_files) == 0:
            raise FileNotFoundError(f"Can not find mapping files for {mapper_tag} MAPPING_PATH={cls._mapping_path}!")

        mapper: Entry = File(mapping_files, mode="r", kind="xml").__entry__()

        if not isinstance(handlers, dict):
            handlers = {}

        # attr = {k[1:]: v for k, v in mapper_config.items() if k.startswith("@")}

        query = uri.query

        uri.query = None

        handlers["*"] = as_entry(uri)

        attr = {"prefix": str(uri), **query}

        for item in mapper.child("spdm/entry/*").search(enable="true"):
            nid = item.get("@id", None)
            if nid is None:
                continue
            handle_uri = item.get("_text", "")
            try:
                handle_uri = handle_uri.format(**attr)
            except KeyError as error:
                pass
                # logger.verbose(f"invaild handle {handle_uri} {error}")
            else:
                handlers[nid] = as_entry(handle_uri)

        cls._mappers[mapper_hash] = mapper, handlers

        return mapper, handlers

    @classmethod
    def _init_mapper(cls):
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
        mapping_path = [pathlib.Path(p) for p in os.environ.get("SP_DATA_MAPPING_PATH", "").split(":") if p != ""]

        mapping_files = []

        mapper_list = cls._mappers

        if local_schema is None:
            local_schema = cls._default_local_schema

        if global_schema is None:
            global_schema = cls._default_global_schema

        uri = uri_split(uri)

        mapper_tag = (local_schema, global_schema, uri.protocol, uri.netloc, uri.path, str(uri.query))


__all__ = ["path", "Mapper"]
