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
from spdm.core.path import Path, PathLike
from spdm.utils.logger import logger
from spdm.utils.misc import normalize_path, serialize
from spdm.utils.path_traverser import PathTraverser
from spdm.utils.tags import _not_found_, _undefined_
from spdm.utils.tree_utils import format_string_recursive


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


@Entry.register("xml")
class XMLEntry(Entry):
    def __init__(self, data: _XMLElement | str, *args, envs={}, **kwargs):
        super().__init__({}, *args, **kwargs)

        if not isinstance(data, str):
            pass
        elif not data.strip(" ").startswith("<"):
            data = load_xml(data)
        else:
            data = fromstring(data)

        self._data: _XMLElement = data

        self._envs = envs

    def __repr__(self) -> str:
        # return f"<{self.__class__.__name__} root={self._root} path={self._path} />"
        return f'<{self._data.tag}  path="{self._path}" />'

    def __copy__(self) -> Entry:
        other: XMLEntry = super().__copy__()  # type:ignore
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
                if p[0] == "@":
                    res += f"[{p}]"
                else:
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

    def _dump(
        self,
        element: _XMLElement | list,
        path=[],
        lazy=False,
        envs=None,
        only_one=False,
        **kwargs,
    ):
        if not isinstance(element, list):
            pass
        elif len(element) == 0:
            return _not_found_
        else:
            res = [self._dump(e, path=path, lazy=lazy, envs=envs, **kwargs) for e in element]
            if len(res) == 1 and not (isinstance(res[0], collections.abc.Mapping) and res[0].get("@id", None) is not None):
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
            res = XMLEntry(element, prefix=[], envs=envs)

        if envs is not None and isinstance(res, (str, collections.abc.Mapping)):
            res = format_string_recursive(res, collections.ChainMap(envs, self._envs))

        return res

    #############################
    # API

    def insert(self, *args, **kwargs) -> XMLEntry:
        raise NotImplementedError(f"")

    def update(self, *args, **kwargs) -> XMLEntry:
        raise NotImplementedError(f"")

    def remove(self, *args, **kwargs) -> int:
        raise NotImplementedError(f"")

    def find(self, op=None, *args, **kwargs) -> typing.Any:

        path = self._path[:]
        xp, envs = self.xpath(path)

        obj: typing.List[_XMLElement] = xp.evaluate(self._data)

        if op is Path.tags.exists:
            return len(obj) > 0
        elif op is Path.tags.count:
            return len(obj)
        elif op is Path.tags.is_leaf:
            if len(obj) == 0:
                return _not_found_
            elif len(obj) > 1:
                return False
            else:
                return len(obj[0]) == 0

        elif op is Path.tags.is_list:
            return len(obj) > 1 or (len(obj) == 1 and obj[0].attrib.get("id", None) != None)

        elif op is Path.tags.is_dict:
            return len(obj) == 1

        elif op is None or op is Path.tags.find:
            return self._dump(obj, path=path, envs=envs, **kwargs)

        else:
            target = self._dump(obj, path=path, envs=envs, **kwargs)

            return Path._apply_op(target, op, [], *args)

    def search_next(self, start=None, **kwargs) -> typing.Tuple[typing.Any, int | None]:

        if len(self._path) > 0 and isinstance(self._path[-1], slice):
            start = self._path[-1].start or start or 0
            stop = self._path[-1].stop
            step = self._path[-1].step or 1
            path = self._path[:-1] + [start]

        elif isinstance(self._path[-1], dict):
            raise NotImplementedError(f"Can not search next element from dict!")

        else:
            if start is None or start is _not_found_:
                start = 0
            path = self._path[:] + [start]
            stop = None
            step = 1

        if stop is not None and start >= stop:
            raise StopIteration(f"{start}>{stop}")

        xp, envs = self.xpath(path)
        data = xp.evaluate(self._data)
        if len(data) == 0:
            raise StopIteration(f"Can not search next element from {path}")
        elif len(data) == 1:
            res = self._dump(data[0], lazy=True, path=path, envs=envs, **kwargs)
            return res, start + step
        else:
            raise RuntimeError(f"Invalid path {path}")

    def for_each(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int, typing.Any], None, None]:
        """Return a generator of the results."""
        if len(self._path) > 0 and isinstance(self._path[-1], slice):
            start = self._path[-1].start or 0
            stop = self._path[-1].stop
            step = self._path[-1].step or 1
            prefix = self._path[:-1]

        elif isinstance(self._path[-1], dict):
            raise NotImplementedError(f"Can not search next element from dict!")

        else:

            start = 0
            stop = None
            step = 1
            prefix = self._path[:]

        next_id = start
        while True:
            if stop is not None and next_id >= stop:
                raise StopIteration(f"{next_id}>{stop}")
            path = prefix + [next_id]
            xp, envs = self.xpath(prefix + [next_id])
            data = xp.evaluate(self._data)
            if len(data) == 0:
                # raise StopIteration(f"Can not search next element from {path}")
                break
            elif len(data) == 1:
                res = self._dump(data[0], lazy=True, path=path, envs=envs, **kwargs)
                yield next_id, res
                next_id += step
            else:
                raise RuntimeError(f"Invalid path {path}")

    #############################

    def _get_value(self, path: PathLike = None, *args, only_one=False, default_value=_not_found_, **kwargs):

        if not only_one:
            return PathTraverser(path).apply(lambda p: self._get_value(p, only_one=True, **kwargs))
        else:
            path = self._prefix + normalize_path(path)
            xp, envs = self.xpath(path)
            obj = xp.evaluate(self._data)
            if isinstance(obj, collections.abc.Sequence) and len(obj) == 1:
                obj = obj[0]
            return self._dump(obj, lazy=False, path=path, envs=envs, **kwargs)

    def search(self, *args, envs={}, **kwargs):
        # path, s_envs = self._xpath(self._path[:])
        # TODO: PathTraverser(path):
        for s_path in self._path.traversal():
            s_path, s_envs = self._xpath(s_path)
            res = _XPath(s_path).evaluate(self._data)

            if len(res) == 0:
                break
            for child in res:
                if child.tag is not _XMLComment:
                    yield self._dump(child, path=s_path, envs=collections.ChainMap(s_envs, envs))

    def items(self, *args, envs={}, **kwargs):
        path = self._path
        for spath in PathTraverser(path):
            xp, s_envs = self.xpath(spath)
            for child in xp.evaluate(self._data):
                if child.tag is _XMLComment:
                    continue
                res = self._dump(child, path=spath, envs=collections.ChainMap(s_envs, envs))
                yield child.tag, res

    def values(self, *args, envs={}, **kwargs):
        path = self._path
        for spath in PathTraverser(path):
            xp, s_envs = self.xpath(spath)
            for child in xp.evaluate(self._data):
                if child.tag is _XMLComment:
                    continue
                res = self._dump(child, path=spath, envs=collections.ChainMap(s_envs, envs))
                yield res

    @property
    def attribute(self):
        return self._data.attrib

    def __serialize__(self):
        return serialize(self.find(default_value=_not_found_))


@File.register(["xml"])
class FILEPLUGINxml(File):
    def __init__(self, *args, root=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.mode == File.Mode.read:
            self._root = load_xml(self.url.path, mode=self.mode)
        else:
            self._root = Element(root or "root")

    def read(self, lazy=True) -> Entry:
        return XMLEntry(self._root, writable=False)

    def write(self, data, *args, **kwargs) -> None:
        tree_to_xml(self._root, data, *args, **kwargs)
        with open(self.url.path, "w") as f:
            f.write(tostring(self._root, pretty_print=True).decode())


__SP_EXPORT__ = FILEPLUGINxml
