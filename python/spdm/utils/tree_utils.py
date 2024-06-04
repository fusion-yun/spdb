import collections.abc
import typing
from copy import copy, deepcopy

import numpy as np

from .logger import deprecated, logger
from .tags import _not_found_, _undefined_
from .typing import primary_type


class DefaultDict(dict):
    """
    This code creates a dictionary that can have a default value for
    keys that are not yet in the dictionary. It creates a dictionary that inherits
    from the built-in dictionary class. It overrides the __missing__ method to
    return a default value if the key is not in the dictionary. It uses a private
    variable, _factory, that is set to the default factory function. It uses the default
    factory function to generate the default value for the key. It sets the default value
    for the key with the __setitem__ method. It returns the default value.
    """

    def __init__(self, default_factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = default_factory

    def __missing__(self, k):
        v = self._factory(k)
        self.__setitem__(k, v)
        return v


_T = typing.TypeVar("_T")


def update_tree(target: _T, key: str | int | list, *args, **kwargs) -> _T:
    pth = None

    if not key and key != 0:
        pass
    elif isinstance(key, str):
        pth = key.split("/")
    elif not isinstance(key, list) and key is not None:
        pth = [key]
    elif len(key) > 0:
        pth = key

    if pth is None:
        if hasattr(target, "_cache"):  # is HTree
            target._cache=update_tree(target._cache, None, *args, **kwargs)

        elif len(args) > 0:
            src = args[0]

            if src is _not_found_:
                pass
            elif target is None or target is _not_found_:
                target = src

            elif target.__class__.__name__ == "HTree":
                target.update(src, **kwargs)

            elif isinstance(target, collections.abc.MutableMapping) and isinstance(src, collections.abc.Mapping):
                # 合并 dict
                for k, v in src.items():
                    update_tree(target, k, v, **kwargs)

            elif kwargs.get("_idempotent", False) is True:
                target = src

            elif isinstance(target, collections.abc.MutableSequence):
                if isinstance(src, collections.abc.Sequence):
                    target.extend(src)
                else:
                    target.append(src)
            elif src is not None:
                target = src

            target = update_tree(target, None, *args[1:], **kwargs)
    else:
        key = pth[0]

        if isinstance(key, str) and key.isdigit():
            key = int(key)

        if isinstance(key, str):
            if target is _not_found_ or target is None:
                target = {}

            # if isinstance(target, collections.abc.MutableMapping):
            if hasattr(target.__class__, key):
                update_tree(getattr(target, key), pth[1:], *args, **kwargs)
            else:
                target[key] = update_tree(target.get(key, _not_found_), pth[1:], *args, **kwargs)

            #     raise RuntimeError(f"Can not update {target} with {key}!")
        else:  # if isinstance(key, int):
            if target is _not_found_ or target is None:
                target = [None] * (key + 1)
            elif isinstance(target, collections.abc.Sequence):
                if key > len(target):
                    target = [*target] + [None] * (key - len(target) + 1)
            # else:
            #     raise TypeError(f"{type(target)} {type(key)}")
            target[key] = update_tree(target[key], pth[1:], *args, **kwargs)

        # else:
        #     raise NotImplementedError(f"{type(key)}")

    return target


 
 

def traversal_tree(d: typing.Any, func: typing.Callable[..., typing.Any]) -> typing.Any:
    if isinstance(d, dict):
        return {k: traversal_tree(v, func) for k, v in d.items()}
    elif isinstance(d, list):
        return [traversal_tree(v, func) for idx, v in enumerate(d)]
    else:
        return func(d)


# def update_tree_recursive(first, second, *args, level=-1, in_place=False, append=False) -> typing.Any:
#     """ 递归合并两个 Hierarchical Tree """
#     if len(args) > 0:
#         return update_tree_recursive(
#             update_tree_recursive(first, second, level=level, in_place=in_place, append=append),
#             *args, level=level, in_place=in_place, append=append)

#     if second is None or second is _not_found_ or level == 0:
#         return first
#     elif first is None or first is _not_found_:
#         return second

#     if in_place:
#         first = copy(first)

#     if isinstance(first, collections.abc.MutableSequence):
#         # 合并 sequence
#         if isinstance(second, collections.abc.Sequence):
#             first.extend(second)
#         else:
#             first.append(second)
#     elif isinstance(first, collections.abc.MutableMapping) and isinstance(second, collections.abc.Mapping):
#         # 合并 dict
#         for k, v in second.items():
#             first[k] = update_tree_recursive(first.get(k, None), v, level=level-1, in_place=in_place)
#     else:
#         first = second
#         # raise TypeError(f"Can not merge {type(first)} with {type(second)}!")

#     return first


class DictTemplate:
    def __init__(self, tmpl, *args, **kwargs):
        self._template = tmpl

    def __missing__(self, key):
        return "{" + key + "}"

    def __getitem__(self, key):
        try:
            res = self._template[key]
        except (KeyError, IndexError):
            raise KeyError(key)

        return res

    def get(self, key, default_value=None):
        try:
            if isinstance(key, str):
                res = _recursive_get(self._template, key.split("."))
            else:
                res = self._template[key]
        except (KeyError, IndexError):
            res = default_value
        return res

    def apply(self, data):
        return tree_apply_recursive(data, lambda s, _template=self: s.format_map(_template), str)[0]


def format_string_recursive(obj, mapping=None):
    class DefaultDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    d = DefaultDict(mapping)
    res, _ = tree_apply_recursive(obj, lambda s, _envs=d: s.format_map(d), str)
    return res


def normalize_data(data):
    """Recursively normalizes JSON data.

    Normalizes JSON data by converting all numeric values to floats, and
    converting all strings to unicode. The types argument is a sequence of
    types that should be converted to strings. It defaults to (int, float,
    str).

    Args:
        data: The JSON data to normalize.
        types: A sequence of types that should be converted to strings.

    Returns:
        The normalized JSON data.
    """
    if isinstance(data, primary_type):
        return data
    elif isinstance(data, collections.abc.Mapping):
        return {k: normalize_data(v) for k, v in data.items()}
    elif isinstance(data, collections.abc.Sequence):
        return [normalize_data(v) for v in data]
    elif isinstance(data, collections.abc.Iterable):
        return [normalize_data(v) for v in data]
    else:
        return str(data)


def tree_apply_recursive(obj, op, types=None):
    """Apply op to all elements in a tree-like structure

    Recursively apply a function to all elements in a tree-like structure
    (list, dict, etc.). The function is applied to all elements of the tree.
    It also supports a list of types to include or exclude from the operation.
    Elements of types in the list are included, and elements of types not in
    the list are excluded. If types is None, all elements are included.

    Args:
        obj: The object to be transformed
        op: The function to apply to each element
        types: A list of types to include or exclude from the operation

    Returns:
        The transformed object and a boolean indicating whether a change was made
    """
    changed = False
    is_attr_tree = False
    if types is not None and isinstance(obj, types):
        try:
            res = op(obj)
        except Exception as error:
            res = None
        else:
            changed = True
        return res, changed

    data = obj

    changed = False

    if not isinstance(data, str) and isinstance(data, collections.abc.Sequence):
        for idx, v in enumerate(data):
            new_v, flag = tree_apply_recursive(v, op, types)
            if flag:
                data[idx] = new_v
                changed = True
    elif isinstance(data, collections.abc.Mapping):
        for idx, v in data.items():
            new_v, flag = tree_apply_recursive(v, op, types)
            if flag:
                data[idx] = new_v
                changed = True

    obj = data

    return obj, changed


###############################################################################
# decperecated functions
#
# 下列function皆已经“废弃”，主要功能已经合并进 Path 和 HTree 两个类


@deprecated
def deep_merge_dict(first: dict | list, second: dict, level=-1, in_place=False, force=False) -> dict | list:
    if not in_place:
        first = deepcopy(first)

    if level == 0:
        return first
    elif isinstance(first, collections.abc.Sequence):
        if isinstance(second, collections.abc.Sequence):
            first.extent(second)
        else:
            first.append(second)
    elif isinstance(first, collections.abc.Mapping) and isinstance(second, collections.abc.Mapping):
        for k, v in second.items():
            d = first.get(k, None)
            if isinstance(d, collections.abc.Mapping):
                deep_merge_dict(d, v, level - 1)
            elif d is None:  # or not isinstance(v, collections.abc.Mapping):
                first[k] = v
    elif second is None:
        pass
    else:
        raise TypeError(f"Can not merge dict with {type(second)}!")

    return first


@deprecated
def reduce_dict(d, **kwargs) -> typing.Dict:
    res = {}
    for v in d:
        deep_merge_dict(res, v, in_place=True, **kwargs)
    return res


def _recursive_get(obj, k):
    return obj if len(k) == 0 else _recursive_get(obj[k[0]], k[1:])


@deprecated
def get_value_by_path(data, path, default_value=None):
    # 将路径按 '/' 分割成列表
    if isinstance(path, str):
        segments = path.split("/")
    elif isinstance(path, collections.abc.Sequence):
        segments = path
    else:
        segments = [path]

    # 初始化当前值为 data
    current_value = data
    # 遍历路径中的每一段
    for segment in segments:
        # 如果当前值是一个字典，并且包含该段作为键
        if isinstance(current_value, collections.abc.Mapping) and segment in current_value:
            # 更新当前值为该键对应的值
            current_value = current_value[segment]
        else:
            # 否则尝试将该段转换为整数索引
            try:
                index = int(segment)
                # 如果当前值是一个列表，并且索引在列表范围内
                if isinstance(current_value, list) and 0 <= index < len(current_value):
                    # 更新当前值为列表中对应索引位置的元素
                    current_value = current_value[index]
                else:
                    # 否则返回默认值
                    return default_value
            except ValueError:
                # 如果转换失败，则返回默认值
                return default_value
    # 返回最终的当前值
    return current_value


@deprecated
def set_value_by_path(data, path, value):
    # 将路径按 '/' 分割成列表
    segments = path.split("/")
    # 初始化当前字典为 data
    current_dict = data
    # 遍历路径中除了最后一段以外的每一段
    for segment in segments[:-1]:
        # 如果当前字典包含该段作为键，并且对应的值也是一个字典
        if segment in current_dict and isinstance(current_dict[segment], dict):
            # 更新当前字典为该键对应的子字典
            current_dict = current_dict[segment]
        else:
            # 尝试将该段转换为整数索引
            try:
                index = int(segment)
                # 如果当前字典不包含该段作为键，或者对应的值不是一个列表
                if segment not in current_dict or not isinstance(current_dict[segment], list):
                    # 创建一个空列表作为该键对应的值
                    current_dict[segment] = []
                # 更新当前字典为该键对应的子列表
                current_dict = current_dict[segment]
            except ValueError:
                # 如果转换失败，则抛出一个异常，提示无法继续查找
                raise Exception(f"Cannot find {segment} in {current_dict}")
    # 在当前字典中设置最后一段作为键，给定的值作为值
    last_segment = segments[-1]
    # 尝试将最后一段转换为整数索引
    try:
        index = int(last_segment)
        # 如果当前字典包含最后一段作为键，并且对应的值是一个列表
        if last_segment in current_dict and isinstance(current_dict[last_segment], list):
            # 判断索引是否在列表范围内
            if 0 <= index < len(current_dict[last_segment]):
                # 更新列表中对应索引位置的元素为给定值
                current_dict[last_segment][index] = value
            else:
                # 否则抛出一个异常，提示无法更新列表元素
                raise Exception(f"Index {index} out of range for list {current_dict[last_segment]}")
        else:
            # 否则直接设置最后一段作为键，给定值作为值（此时会创建一个单元素列表）
            current_dict[last_segment] = value
    except ValueError:
        # 如果转换失败，则直接设置最后一段作为键，给定值作为值（此时会覆盖原有列表）
        current_dict[last_segment] = value

    return True


@deprecated
def get_value(*args, **kwargs) -> typing.Any:
    return get_value_by_path(*args, **kwargs)


@deprecated
def get_many_value(
    d: collections.abc.Mapping, name_list: collections.abc.Sequence, default_value=None
) -> collections.abc.Mapping:
    return {k: get_value(d, k, get_value(default_value, idx)) for idx, k in enumerate(name_list)}


@deprecated
def set_value(*args, **kwargs) -> bool:
    return set_value_by_path(*args, **kwargs)


@deprecated
def try_get(obj, path: str, default_value=_undefined_):
    if obj is None or obj is _not_found_:
        return default_value
    elif path is None or path == "":
        return obj

    start = 0
    path = path.strip(".")
    s_len = len(path)
    while start >= 0 and start < s_len:
        pos = path.find(".", start)
        if pos < 0:
            pos = s_len
        next_obj = getattr(obj, path[start:pos], _not_found_)

        if next_obj is not _not_found_:
            obj = next_obj
        elif isinstance(obj, collections.abc.Mapping):
            next_obj = obj.get(path[start:pos], _not_found_)
            if next_obj is not _not_found_:
                obj = next_obj
            else:
                break
        else:
            break

        start = pos + 1
    if start > s_len:
        return obj
    elif default_value is _undefined_:
        raise KeyError(f"Can for find path {path}")
    else:
        return default_value


@deprecated
def try_getattr_r(obj, path: str):
    if path is None or path == "":
        return obj, ""
    start = 0
    path = path.strip(".")
    s_len = len(path)
    while start >= 0 and start < s_len:
        pos = path.find(".", start)
        if pos < 0:
            pos = s_len
        if not hasattr(obj, path[start:pos]):
            break
        obj = getattr(obj, path[start:pos])
        start = pos + 1
    return obj, path[start:]


@deprecated
def getattr_r(obj, path: str):
    # o, p = try_getattr_r(obj, path)

    # if p != '':
    #     raise KeyError(f"Can for find path {path}")
    if type(path) is str:
        path = path.split(".")

    o = obj
    for p in path:
        o = getattr(o, p, None)
        if o is None:
            break
            # raise KeyError(f"Can not get attribute {p} from {o}")
    return o


@deprecated
def getitem(obj, key=None, default_value=None):
    if key is None:
        return obj
    elif hasattr(obj, "__get__"):
        return obj.__get__(key, default_value)
    elif hasattr(obj, "__getitem__"):
        return obj.__getitem__(key) or default_value
    else:
        return default_value


@deprecated
def setitem(obj, key, value):
    if hasattr(obj, "__setitem__"):
        return obj.__setitem__(key, value)
    else:
        raise KeyError(f"Can not setitem {key}")


@deprecated
def iteritems(obj):
    if obj is None:
        return []
    elif isinstance(obj, collections.abc.Sequence):
        return obj
    elif isinstance(obj, collections.abc.Mapping):
        return obj.items()
    else:
        raise TypeError(f"Can not apply 'iteritems' on {type(obj)}!")
