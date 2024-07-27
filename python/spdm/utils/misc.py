import collections
import collections.abc
import dataclasses
import functools
import importlib
import inspect
import io
import json
import os
import pathlib
import pkgutil
import pwd
import re
import sys
import typing
from enum import Flag, auto
from typing import Sequence, Type
from urllib.parse import ParseResult, urlparse

import numpy as np

from .logger import logger
from .tags import _empty, _not_found_, _undefined_

import re


def camel_to_snake(name):
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)


def float_unique(d: np.ndarray, x_min=-np.inf, x_max=np.inf) -> np.ndarray:
    if not isinstance(d, np.ndarray):
        d = np.asarray(d)
    d = np.sort(d)
    tag = np.append(True, np.diff(d)) > np.finfo(float).eps * 10
    rtag = np.logical_and(d >= x_min, d <= x_max)
    rtag = np.logical_or(rtag, np.isclose(d, x_min, rtol=1e-8))
    rtag = np.logical_or(rtag, np.isclose(d, x_max, rtol=1e-8))
    tag = np.logical_and(tag, rtag)
    return d[tag]


def array_like(x: np.ndarray, d):
    if isinstance(d, np.ndarray):
        return d
    elif isinstance(d, (int, float)):
        return np.full_like(x, d)
    elif callable(d):
        return np.asarray(d(x))
    else:
        return np.zeros_like(x)
    # else:
    #     raise TypeError(type(d))


def try_hash(obj) -> int:

    if isinstance(obj, dict):
        # 字典键值顺序不影响 hash
        keys = [*obj.keys()]
        keys.sort()
        return hash(tuple([hash(tuple([hash(k), try_hash(obj[k])]) for k in keys)]))
    elif isinstance(obj, (list, tuple)):
        return hash(tuple([try_hash(v) for v in obj]))
    elif hasattr(obj.__class__, "__hash__"):
        return hash(obj)
    else:
        return hash(obj)


# _empty = object()


# class _NOT_FOUND_:
#     def _as_dict(self):
#         return {}

#     def _as_list(self):
#         return []

#     def __serialize__(self):
#         return None


# class _tags(Flag):
#     not_found = auto()
#     undefined = auto()


# _not_found_ = _tags.not_found

# _undefined_ = _tags.undefined


def whoami(obj=None):
    cls = getattr(obj, "__class__", None)
    if cls is not None:
        return f"{cls.__name__}.{inspect.stack()[1][3]}"
    else:
        return inspect.stack()[1][3]


def get_cls_file_path(cls):
    return pathlib.Path(inspect.getfile(cls)).parent


def load_pkg_data(pkgname, path):
    data = pkgutil.get_data(pkgname, path)
    return json.loads(data.decode("utf-8"))


# def try_get(holder, path, default_value=None):
#     path = normalize_path(path)
#     obj = holder

#     for k in path:
#         if isinstance(k, str):
#             next_o = getattr(obj, k, _not_found_)

#             op = getattr(obj.__class__, k, None)
#         else:
#             op = None
#         if op is None:
#             try:
#                 data = obj.__getitem__(k)
#             except Exception:
#                 obj = default_value
#                 break
#             # except IndexError as error:
#             #     raise IndexError(f"{k} > {len(obj)} Error: {error}")
#             else:
#                 obj = data

#         elif isinstance(op, functools.cached_property):
#             obj = op.__get__(obj)
#         elif isinstance(obj, property):
#             obj = op(obj, "fget")(obj)
#         else:
#             obj = default_value

#     return obj


def try_put(holder, path, value):
    res = None
    if isinstance(path, str):
        res = getattr(holder.__class__, path, None)
    if res is None:
        holder.__setitem__(path, value)
    elif isinstance(res, property):
        getattr(res, "fset")(holder, path, value)
    else:
        raise KeyError(f"Can not set attribute {value}!")

    # def try_getitem_r(obj, path):
    #     if path is None or path == '':
    #         return obj, ''
    #     start = 0
    #     path = path.strip(".")
    #     s_len = len(path)
    #     while start >= 0 and start < s_len:
    #         pos = path.find('.', start)
    #         if pos < 0:
    #             pos = s_len
    #         if isinstance(obj, collections.abc.Mapping) and path[start:pos] in obj:
    #             obj = obj.get(path[start: pos])
    #             start = pos+1
    #         else:
    #             break
    #     return obj, path[start:]

    # def getitem_r(obj, path: str):
    #     o, p = try_getitem_r(obj, path)
    #     if p != '':
    #         raise KeyError(f"Can for find path {path}")
    #     return o


def normalize_path(path):
    if path is None:
        path = []
    elif isinstance(path, str):
        path = path.split(".")
    elif not isinstance(path, collections.abc.MutableSequence):
        path = [path]
    return path


def serialize(d):
    if isinstance(d, (int, float, str)):
        return d
    elif hasattr(d, "__array__"):  # numpy.ndarray like
        return d.__array__()
    elif hasattr(d.__class__, "__serialize__"):
        return d.__serialize__()
    elif dataclasses.is_dataclass(d):
        return {f.name: serialize(getattr(d, f.name)) for f in dataclasses.fields(d)}
    elif isinstance(d, collections.abc.Mapping):
        return {k: serialize(v) for k, v in d.items()}
    elif isinstance(d, collections.abc.Sequence):
        return [serialize(v) for v in d]
    else:
        # logger.warning(f"Can not serialize {d.__class__.__name__}!")
        return f"<{d.__class__.__name__}>NOT_SERIALIZABLE!</{d.__class__.__name__}>"
        # raise TypeError(f"Can not serialize {type(d)}!")


def as_file_fun(func=None, *f_args, **f_kwargs):
    """Function wrapper: Convert  first argument (as file path) to File object
    TODO salmon (20190915): specify the position/key of the file path argument
    """

    def _decorate(wrapped):
        @functools.wraps(wrapped)
        def _wrapper(fp, *args, **kwargs):
            if isinstance(fp, str):
                with open(fp, *f_args, **f_kwargs) as fid:
                    res = wrapped(fid, *args, **kwargs)
            elif isinstance(fp, pathlib.Path):
                with fp.open(*f_args, **f_kwargs) as fid:
                    res = wrapped(fid, *args, **kwargs)
            elif isinstance(fp, io.IOBase):
                res = func(fp, *args, **kwargs)
            else:
                raise TypeError(f"Can not convert type({type(fp)}) to file-like object!")

            return res

        return _wrapper

    if func is None:
        return _decorate
    else:
        return _decorate(func)


def as_lazy_object(func, *f_args, **f_kwargs):
    def _decorate(wrapped):
        @functools.wraps(wrapped)
        def _wrapper(*args, **kwargs):
            def fun():
                return wrapped(*args, **kwargs)

            return LazyProxy(fun)

        return _wrapper

    if func is None:
        return _decorate
    else:
        return _decorate(func)


def getlogin():
    try:
        return os.getlogin()
    except Exception:
        return pwd.getpwuid(os.getuid())[0]


def get_username():
    return getlogin()


def _gusses_name(self, name_hint):
    count = sum(1 for k, v in self._graph.nodes.items() if k == name_hint or k.startswith(f"{name_hint}_"))
    if count > 0:
        name_hint = f"{name_hint}_{count}"
    return name_hint


def _try_insert(self, name_hint, node):
    return self.add_node(node, label=self._gusses_name(name_hint or node.__class__.__name__.lower()))


def compile_regex_pattern(pattern):
    try:
        res = re.compile(pattern)
    except re.error:
        res = None
    finally:
        return res


def first_not_empty(*args):
    return next(x for x in args if len(x) > 0)


def guess_class_name(obj):
    if not inspect.isclass(obj):
        cls = obj.__class__
        cls_name = getattr(obj, "__orig_class__", None)
    else:
        cls = obj
        cls_name = None

    return cls_name or f"{cls.__module__}.{cls.__name__}"


def find_duplicate(l: Sequence, atol=1.0e-8):
    for i, val in enumerate(l[:-1]):
        idx = np.flatnonzero(np.abs(l[i + 1 :] - val) < atol)
        if len(idx) > 2:
            yield idx + i


def replace_tokens(value: str, env):
    class _TokenProxy:
        def __init__(self, d):
            if isinstance(d, _TokenProxy):
                self._data = d._data
            else:
                self._data = d

        def __getitem__(self, key):
            value = get_value_by_path(self._data, key.split("."), _not_found_)
            if value is _not_found_:
                return "{" + key + "}"
            else:
                return value

    if isinstance(value, str):
        # 使用 format_map() 方法进行替换，并更新 document 中的 value
        return value.format_map(_TokenProxy(env))
    elif isinstance(value, list):
        return [replace_tokens(v, env) for v in value]
    elif isinstance(value, dict):
        return {k: replace_tokens(v, env) for k, v in value.items()}
    else:
        return value


def fetch_request(url: str) -> typing.Dict:
    """
    根据路径拖回并解析module_file
    """
    if not isinstance(url, ParseResult):
        url = urlparse(url)
    content = None

    if url.scheme in ["http", "https"]:
        # path is a uri
        response = requests.get(url)
        if response.status_code == 200:
            # request is successful
            content = yaml.safe_load(response.text)  # parse the response text as yaml
        else:
            raise FileNotFoundError(url)
    elif url.scheme in ["local", "file", ""]:
        if not os.path.isfile(url.path):
            raise FileNotFoundError(url.path)
        # file exists
        with open(url.path, "r") as file:
            content = yaml.safe_load(file)  # parse the file content as yaml
    else:
        raise NotImplementedError(url)

    return content


primitive_types = (int, bool, str, float, complex, np.ndarray)

builtin_types = (int, bool, str, float, complex, list, dict, set, tuple, np.ndarray)


def group_dict_by_prefix(
    d: collections.abc.Mapping, prefixes: str | typing.List[str], keep_prefix=False, sep="_"
) -> typing.Tuple[typing.Dict, ...]:
    """将 字典 d 根据prefixs进行分组
    prefix 是一个字符串，或者是一个字符串列表
    key具有相同prefix的项会被分到一组， (if keep_prefix is True then prefix会被去掉)
    返回值是一个元组，每元素是分组后的字典，最后一个元素是其他项的字典
    """

    if isinstance(prefixes, str):
        prefixes = prefixes.split(",")

    groups = [None] * len(prefixes) + [{}]

    for key, value in d.items():
        for idx, prefix in enumerate(prefixes):
            if not key.startswith(prefix):
                continue

            if key == prefix:
                if groups[idx] is None:
                    groups[idx] = value
                elif isinstance(value, collections.abc.Mapping):
                    groups[idx].update(value)
                else:
                    raise ValueError(f"prefix {prefix} is not unique")
            else:
                if sep is not None:
                    prefix = prefix + sep

                if not key.startswith(prefix):
                    continue

                if not keep_prefix:
                    key = key[len(prefix) :]

                if groups[idx] is None:
                    groups[idx] = {}
                elif not isinstance(groups[idx], collections.abc.Mapping):
                    raise ValueError(f"prefix {prefix} is not a dict, but {groups[idx]}")

                groups[idx][key] = value
            break
        else:
            groups[-1][key] = value
    return tuple(groups)


def get_positional_argument_count(function):
    """
    获得一个 function 能够接纳的位置参数个数

    Args:
        function: 要获取的函数

    Returns:
        位置参数个数
    """

    import inspect

    signature = inspect.signature(function)
    positional_only_parameters = [
        parameter for parameter in signature.parameters if parameter == inspect.Parameter.POSITIONAL_ONLY
    ]
    return len(positional_only_parameters)


def fun():
    if isinstance(prefixs, str):
        prefixs = [prefixs]

    prefix_dict = {}

    if isinstance(obj, dict):
        prefix_dict = obj
        obj = None

    prefix_len = len(prefix)
    other_dict = {}
    for k, v in d.items():
        if k.startswith(prefix):
            if not keep_prefix:
                k = k[prefix_len:]
            if not isinstance(v, dict) or not isinstance(prefix_dict.get(k, None), dict):
                prefix_dict[k] = v
            else:
                prefix_dict[k] |= v

        elif k != prefix[:-1]:
            other_dict[k] = v

    if obj is None:
        return prefix_dict, other_dict
    else:
        if len(prefix_dict) > 0:
            raise RuntimeWarning(f" {prefix}*  {prefix_dict} are ignored")

        return obj, other_dict
