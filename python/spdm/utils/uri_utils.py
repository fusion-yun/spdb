"""
Feature:
 * This module defines functions for Uniform Resource Identifier (URI) string,
    following the syntax specifications in RFC 3986.
 * This module support extended 'Path' syntax, supports bracket '[]' in the path.
 TODO (salmon.20190919): support  quoting
"""
import ast
import collections
import collections.abc
import pathlib
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Union
from urllib.parse import parse_qs, urlparse

from .logger import logger

_rfc3986 = re.compile(
    r"^((?P<protocol>[^:/?#]+):)?(//(?P<authority>[^/?#]*))?(?P<path>[^?#]*)(\?(?P<query>[^#]*))?(#(?P<fragment>.*))?")

_rfc3986_ext0 = re.compile(
    r"^((?P<schema>[^:/?#\+\[\]]+)?(\+(?P<protocol>[^:/?#\+\[\]]+))?:)?(//(?P<authority>[^/?#]*))?(?P<path>[^?#]*)(\?(?P<query>[^#]*))?(#(?P<fragment>.*))?")

_rfc3986_ext = re.compile(
    r"^((?P<protocol>[^:/?#\+\[\]]+)?(\+(?P<format>[^:/?#\+\[\]]+))?(\[(?P<schema>[^:/?#\+\[\]]*)\])?:)?(//(?P<authority>[^/?#]*))?(?P<path>[^?#]*)(\?(?P<query>[^#]*))?(#(?P<fragment>.*))?")


@dataclass
class URITuple:
    protocol: str = None
    authority: str = None
    path: str = None
    query: dict = None
    fragment: str = None


def uri_split_as_dict(uri) -> dict:
    if uri is None:
        uri = ""
    elif isinstance(uri, URITuple):
        return uri.__dict__

    # res = _rfc3986_ext0.match(uri).groupdict()

    url = urlparse(uri)

    query = "{" + ','.join([(f'"{k}":"{v[0]}"' if not v[0].isnumeric() else f'"{k}":{v[0]}')
                           for k, v in parse_qs(url.query).items()])+"}"
    ast.literal_eval(query)
    res = dict(
        protocol=url.scheme,
        authority=url.netloc,
        path=url.path,
        query=ast.literal_eval(query),
        fragment=ast.literal_eval(url.fragment) if url.fragment != "" else url.fragment
    )
    return res


def uri_split(uri: Union[str, URITuple, Path]) -> URITuple:
    if isinstance(uri, URITuple):
        return deepcopy(uri)
    elif isinstance(uri, str):
        return URITuple(**uri_split_as_dict(uri))
    elif isinstance(uri, (collections.abc.Sequence, Path)):
        return URITuple(path=uri)
    else:
        raise TypeError(uri)


def uri_merge(schema, authority=None, path=None,  query=None, fragment=None):

    return "".join([
        schema+"://" if schema is not None else "",
        (authority or "").strip('/'),
        path or "",
        "?"+str(query) if query is not None else "",
        "#"+str(fragment) if fragment is not None else ""
    ])


def uri_join(base, uri):
    o0 = uri_split(base) if not isinstance(
        base, collections.abc.Mapping) else base
    o1 = uri_split(uri) if not isinstance(uri, collections.abc.Mapping) else uri
    if o1.schema is not None and o1.schema != o0.schema:
        return uri
    elif o1.authority is not None and o1.authority != o0.authority:
        schema = o0.schema
        authority = o1.authority
        path = o1.path
    else:
        schema = o0.schema
        authority = o0.authority

        if o1.path is None or o1.path == '':
            path = o0.path
        elif o1.path is not None and len(o1.path) > 0 and o1.path[0] == '/':
            path = o1.path
        else:
            path = o0.path[:o0.path.rfind('/')]+"/"+o1.path

    return uri_merge(schema, authority, path, o1.query, o1.fragment)


def uridefrag(uri):
    o = uri_split(uri)
    return uri_merge(o.schema, o.authority, o.path, None, None), o.fragment


_r_path_item = re.compile(
    r"([a-zA-Z_\$][^./\\\[\]]*)|\[([+-]?\d*)(?::([+-]?\d*)(?::([+-]?\d*))?)?\]")


class _Empty:
    pass


def _ion(v):
    """if v is not return int(v) else return None"""
    return int(v) if v is not None and v != '' else None


def parse_url_iter(path, with_position=False):
    """ obj : object like dict or list
        path:
            i.e.  a.b.d[23][3:3:4].adf[3]
        try_attr: if true then try to get attribute  when getitem failed

    """

    for m in _r_path_item.finditer(path):
        attr, start, stop, step = m.groups()
        if attr is not None:
            idx = attr
        elif stop is None and step is None:
            idx = _ion(start)
        else:
            idx = slice(_ion(start), _ion(stop), _ion(step))

        if with_position:
            yield idx, m.end()
        else:
            yield idx


def normalize_path_to_list(path, split=True):
    if isinstance(path, str):
        if split:
            path = parse_url_iter(path)
        else:
            path = [path]
    elif not isinstance(path, collections.abc.Sequence):
        path = [path]
    return path


def getitem_by_path(obj, path, *, try_attribute=False, split=True):
    path = normalize_path_to_list(path, split)

    if path is None:
        return obj

    for idx in path:
        if isinstance(obj, tuple):
            if isinstance(idx, str):
                obj = getattr(obj, idx)
            else:
                obj = obj[idx]
        elif isinstance(obj, collections.abc.Mapping):
            obj = obj[idx]
        elif isinstance(obj, collections.abc.Sequence) and \
                (isinstance(idx, int) or isinstance(idx, slice)):
            obj = obj[idx]
        elif try_attribute and isinstance(idx, str) and hasattr(obj, idx):
            obj = getattr(obj, idx)
        else:
            raise IndexError(idx)
    return obj


def setitem_by_path(obj, path: str, data, *, try_attribute=True, split=True):
    path = normalize_path_to_list(path, split)

    if path is None:
        return obj

    prev_idx = None

    for idx in path:
        if prev_idx is None:
            pass
        elif isinstance(obj, tuple):
            if isinstance(prev_idx, str):
                obj = getattr(obj, prev_idx)
            else:
                obj = obj[idx]
        elif isinstance(obj, collections.abc.Mapping) and not isinstance(idx, slice):
            obj = obj.setdefault(prev_idx, {})
        elif isinstance(obj, collections.abc.Sequence):
            obj = obj[prev_idx]
        elif try_attribute and isinstance(prev_idx, str):
            obj = getattr(obj, prev_idx)
        else:
            raise IndexError(f"Insert item error {idx} !")
        prev_idx = idx

    if isinstance(obj, tuple):
        raise AttributeError("Can't set attribute to tuple")
    elif isinstance(obj, collections.abc.MutableMapping) or isinstance(obj, collections.abc.MutableSequence):
        obj[prev_idx] = data
    elif try_attribute and isinstance(prev_idx, str) and hasattr(obj, prev_idx):
        setattr(obj, prev_idx, data)
    else:
        raise IndexError(f"Set item error! {obj} {path}")


def getvalue_r(obj, path):
    return getitem_by_path(obj, path, try_attribute=True)


def setvalue_r(obj, path, data):
    return setitem_by_path(obj, path, data, try_attribute=True)


def pathslit(path: Union[List, str], delimiter='/') -> List:
    if isinstance(path, str):
        path = path.split(delimiter)
    return path
