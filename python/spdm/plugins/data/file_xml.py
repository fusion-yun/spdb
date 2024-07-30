from __future__ import annotations

import collections
import collections.abc
import pathlib
import typing

import numpy as np
from lxml.etree import Comment as _XMLComment
from lxml.etree import ParseError as _XMLParseError
from lxml.etree import XPath as _XPath
from lxml.etree import _Element as _XMLElement
from lxml.etree import Element as Element

from lxml.etree import fromstring, tostring
from lxml.etree import parse as parse_xml
from spdm.core.entry import Entry
from spdm.core.file import File
from spdm.core.path import Path, PathLike, Query
from spdm.utils.logger import logger
from spdm.utils.misc import normalize_path, serialize
from spdm.utils.path_traverser import PathTraverser
from spdm.utils.tags import _not_found_, _undefined_
from spdm.utils.tree_utils import format_string_recursive
from spdm.utils.uri_utils import uri_split


def merge_xml(first, second):
    if first is None:
        raise ValueError(f"Try merge to None Tree!")
    elif second is None:
        return first
    elif first.tag != second.tag:
        raise ValueError(f"Try to merge tree to different tag! {first.tag}<={second.tag}")

    for child in second:
        if child.tag is _XMLComment:
            continue
        eid = child.attrib.get("id", None)
        if eid is not None:
            target = first.find(f"{child.tag}[@id='{eid}']")
        else:
            target = first.find(child.tag)
        if target is not None:
            merge_xml(target, child)
        else:
            first.append(child)


def load_xml(path: str | list | pathlib.Path, *args, mode: File.Mode | str = "r", **kwargs):
    # TODO: add handler non-local request ,like http://a.b.c.d/babalal.xml

    if isinstance(path, list):
        root = None
        for fp in path:
            if root is None:
                root = load_xml(fp, mode=mode)
            else:
                merge_xml(root, load_xml(fp, mode=mode))
        return root

    if isinstance(path, str):
        path = pathlib.Path(path)

    root = None
    path = pathlib.Path(path)
    if path.exists() and path.is_file():
        try:
            if isinstance(path, pathlib.Path):
                root = parse_xml(path.as_posix()).getroot()
            elif isinstance(path, str):
                root = parse_xml(path).getroot()
            else:
                raise TypeError(f"Invalid path type: {type(path)}")
            # logger.debug(f"Loading XML file from {path}")
        except _XMLParseError as msg:
            raise RuntimeError(f"ParseError: {path}: {msg}")
    else:
        raise FileNotFoundError(path)

    if root is not None:
        for child in root.findall("{http://www.w3.org/2001/XInclude}include"):
            fp = path.parent / child.attrib["href"]
            root.insert(0, load_xml(fp))
            root.remove(child)

    return root


def tree_to_xml(root: str | Element, d, *args, **kwargs) -> _XMLElement:
    if isinstance(root, str):
        root = Element(root)

    for key, val in d.items():
        if isinstance(val, dict):
            child = tree_to_xml(key, val)
            root.append(child)
        elif isinstance(val, list):
            for i, v in enumerate(val):
                child = tree_to_xml(key, v)
                child.set("id", str(i))
                root.append(child)

        elif isinstance(val, np.ndarray):
            child = Element(key)
            if np.issubdtype(val.dtype, np.floating):
                child.set("dtype", "float")
            elif np.issubdtype(val.dtype, np.integer):
                child.set("dtype", "int")
            else:
                logger.debug(val.dtype)
            child.set("shape", str(list(val.shape)).strip("[]"))
            text = str(val.tolist())
            text = text.strip("[]")

            child.text = text
            root.append(child)
        else:
            child = Element(key)
            child.text = str(val)
            root.append(child)

    return root


class FileXML(File, plugin_name="xml"):

    class Entry(File.Entry):
        def __init__(self, data, *args, envs=None, **kwargs):

            if isinstance(data, str) and data.strip(" ").startswith("<"):
                data = fromstring(data)
            else:
                data = load_xml(data.path)

            super().__init__(_not_found_, *args, **kwargs)

            self._data: _XMLElement = data

            self._envs = envs

        def __repr__(self) -> str:
            # return f"<{self.__class__.__name__} root={self._root} path={self._path} />"
            return f'<{self._data.tag}  path="{self._path}" />'

        def __copy__(self) -> typing.Self:
            other: typing.Self = super().__copy__()
            other._envs = self._envs
            other._data = self._data
            return other

        def _xpath(self, path):
            envs = {}
            res = "."
            prev = None
            for p in path:
                if isinstance(p, int):
                    res += f"[(position()= {p+1} and @id ) or (@id={p}) or @id='*']"
                    envs[prev] = p
                # # elif isinstance(p, slice):
                # #     if p == slice(None):
                # #         res += "[@id]"
                # #     else:
                # #         raise NotImplementedError("XML DO NOT SUPPORT SLICE!")
                # elif isinstance(p, (tuple, set)):
                #     raise NotImplementedError(f"XML DO NOT SUPPORT TUPLE OR SET!{path}")
                elif isinstance(p, str) and len(p) > 0:
                    # if p[0] == "@":
                    #     res += f"[{p}]"
                    # else:
                    res += f"/{p}"
                    prev = p
                else:
                    envs[prev] = p
                    # # TODO: handle slice
                    # raise TypeError(f"Illegal path type! {type(p)} {path}")

            return res, envs

        def xpath(self, path):
            p, e = self._xpath(path)
            return _XPath(p), e

        #############################
        # API

        def insert(self, *args, **kwargs) -> typing.Self:
            return super().insert(*args, **kwargs)

        def update(self, *args, **kwargs) -> typing.Self:
            return super().update(*args, **kwargs)

        def delete(self, *args, **kwargs) -> int:
            return super().delete(*args, **kwargs)

        def find(self, *args, default_value=_not_found_, **kwargs) -> typing.Any:
            if self._cache is not _not_found_:
                res = super().find(*args, default_value=_not_found_, **kwargs)
                if res is not _not_found_:
                    return res

            path = self._path[:]
            xp, envs = self.xpath(path)

            obj: typing.List[_XMLElement] = xp(self._data)

            # res = Path._project(obj, *args, **kwargs)
            if len(args) > 0:
                op = args[0]
                args = args[1:]
            else:
                op = Query.tags.get_value

            match op:
                case Query.tags.exists:
                    res = len(obj) > 0
                case Query.tags.count:
                    res = len(obj)
                case Query.tags.is_leaf:
                    if len(obj) == 0:
                        res = _not_found_
                    elif len(obj) > 1:
                        res = False
                    else:
                        res = len(obj[0]) == 0
                case Query.tags.is_list:
                    res = len(obj) > 1 or (len(obj) == 1 and obj[0].attrib.get("id", None) != None)
                case Query.tags.is_dict:
                    res = len(obj) == 1

                case Query.tags.get_value:
                    res = self._dump(obj, path=path, envs=envs, **kwargs)

                case Query.tags.get_item:
                    res = "/".join(path), self._dump(obj, path=path, envs=envs, **kwargs)

                case Query.tags.get_key:
                    res = "/".join(path)

                case _:
                    target = self._dump(obj, path=path, envs=envs, **kwargs)
                    res = Path._project(target, op, *args, default_value=default_value, **kwargs)

            return res

        def search(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int, typing.Any], None, None]:
            """Return a generator of the results."""

            xp, envs = self.xpath(self._path[:])

            for data in xp.evaluate(self._data):
                yield Path._project(self._dump(data, lazy=True, path=self._path, envs=envs), *args, **kwargs)

        def flush(self):
            """将缓存内的数据写入持久存储（文件）"""
            raise NotImplementedError("Not implemented yet!")

        def load(self):
            """将持久存储（文件）导入缓存"""
            self._cache = self._path.update(self._cache, self._dump(self._data, self._path))

        def _dump(
            self,
            element: _XMLElement | list,
            path=None,
            lazy=False,
            envs=None,
            **kwargs,
        ):
            if isinstance(element, _XMLElement):
                pass
            elif not isinstance(element, list):
                return element
            elif len(element) == 0:
                return _not_found_
            else:
                res = [self._dump(e, path=path, lazy=lazy, envs=envs, **kwargs) for e in element]
                if len(res) == 1 and not (
                    isinstance(res[0], collections.abc.Mapping) and res[0].get("@id", None) is not None
                ):
                    return res[0]
                else:
                    return res

            # elif len(path) > 0 and isinstance(path[-1], slice):
            #     raise NotImplementedError(f"{path}")

            # else:
            #     res = [self._dump(e, path=path, lazy=lazy, envs=envs, **kwargs) for e in element]

            #     if isinstance(res[0], dict) and res[0].get("@id", None) is not None:
            #         pass
            #     elif only_one or len(res) == 1:
            #         res = res[0]

            #     return res

            res = None
            text = element.text.strip() if element.text is not None else None
            if text is not None and len(text) > 0:
                if "dtype" in element.attrib or (len(element) == 0 and len(element.attrib) == 0):
                    dtype = element.attrib.get("dtype", None)
                    if dtype == "string" or dtype is None:
                        res = [text]
                    elif dtype == "int":
                        res = [int(v.strip()) for v in text.strip(",").split(",")]
                    elif dtype == "float":
                        res = [float(v.strip()) for v in text.strip(",").split(",")]
                    else:
                        raise NotImplementedError(f"Not supported dtype {dtype}!")

                    dims = [int(v) for v in element.attrib.get("dims", "").split(",") if v != ""]
                    if len(dims) == 0 and len(res) == 1:
                        res = res[0]
                    elif len(dims) > 0 and len(res) != 0:
                        res = np.array(res).reshape(dims)
                    else:
                        res = np.array(res)
                elif len(element.attrib) == 0:
                    res = text
                else:
                    res = {}
                    for k, v in element.attrib.items():
                        res[f"@{k}"] = v
                    res["_text"] = text

            elif not lazy:
                res = {}
                for child in element:
                    if child.tag is _XMLComment:
                        continue
                    obj = self._dump(child, path=path + [child.tag], envs=envs, lazy=lazy, **kwargs)
                    old = res.get(child.tag, None)
                    if old is None:
                        if isinstance(obj, dict) and obj.get("@id", None) is not None:
                            res[child.tag] = [obj]
                        else:
                            res[child.tag] = obj
                    elif isinstance(old, list):
                        old.append(obj)
                    else:
                        res[child.tag] = [old, obj]

                # res = {child.tag: self._convert(child, path=path+[child.tag], envs=envs, lazy=lazy, **kwargs)
                #        for child in element if child.tag is not _XMLComment}
                for k, v in element.attrib.items():
                    res[f"@{k}"] = v

                text = element.text.strip() if element.text is not None else None
                if text is not None and len(text) != 0:
                    query = {}
                    prev = None
                    for p in self._prefix + path:
                        if type(p) is int:
                            query[f"{prev}"] = p
                        prev = p

                    # if not self._envs.fragment:
                    #     fstr = query
                    # else:
                    #     fstr = collections.ChainMap(query, self.envs.fragment.__data__, self.envs.query.__data__ or {})
                    # format_string_recursive(text, fstr)  # text.format_map(fstr)
                    res["@text"] = text

            else:
                res = EntryXML(element, prefix=[], envs=envs)

            if envs is not None and isinstance(res, (str, collections.abc.Mapping)):
                if self._envs is not None:
                    envs = collections.ChainMap(envs, self._envs)

                res = format_string_recursive(res, envs)

            return res

    def read(self, *args, **kwargs) -> typing.Any:
        "读取"
        return self.__entry__().find(*args, **kwargs)

    def write(self, *args, **kwargs) -> None:
        "写入"
        return self.__entry__().update(*args, **kwargs)
