from __future__ import annotations

import collections.abc
import dataclasses
import inspect
import pprint
import typing
from copy import copy
from enum import Enum
import typing
import numpy as np

from ..utils.logger import logger
from ..utils.misc import as_dataclass, typing_get_origin
from ..utils.tags import _not_found_, _undefined_
from ..utils.typing import array_type, primary_type, PrimaryType
from ..utils.numeric import as_array, is_close, is_scalar
from ..utils.tree_utils import _recursive_get
from .Entry import Entry, as_entry
from .Path import Path, PathLike, as_path, path_like

_T = typing.TypeVar("_T")


class Node(typing.Generic[_T]):
    """
        节点类，用于表示数据结构中的节点，节点可以是一个标量（或 array_type），也可以是一个列表，也可以是一个字典。
        用于在一般数据结构上附加类型标识（type_hint)。

        @NOTE:
            - Node,Dict,List 不缓存__getitem__结果
            - __getitem__ 返回的类型由 __type_hint__ 决定，默认为 Node
        -
    """

    _MAPPING_TYPE_ = dict
    _SEQUENCE_TYPE_ = list

    def __init__(self, d: typing.Any,
                 parent: Node = None,
                 default_value: typing.Any = None,
                 metadata: typing.Dict[str, typing.Any] = None,
                 **kwargs) -> None:

        if metadata is None or metadata is _not_found_:
            metadata = kwargs
            kwargs = {}

        if self.__class__ is not Node or isinstance(d, primary_type) or isinstance(d, Entry):
            pass
        elif isinstance(d, collections.abc.Sequence):  # 如果 entry 是列表, 就把自己的类改成列表
            self.__class__ = Node._SEQUENCE_TYPE_

        elif isinstance(d, collections.abc.Mapping):  # 如果 entry 是字典, 就把自己的类改成字典
            self.__class__ = Node._MAPPING_TYPE_

        # if d is _not_found_ or d is None:
        #     raise RuntimeError(f"{d} is not a valid value")

        self._entry = as_entry(d)
        self._default_value = default_value
        self._parent = parent
        self._metadata = metadata
        self._cache = {}

        # if len(kwargs) > 0:
        #     raise RuntimeError(f"Ignore kwargs={kwargs}")

    def __copy__(self) -> Node:
        other: Node = self.__class__.__new__(self.__class__)
        other._entry = copy(self._entry)
        other._metadata = copy(self._metadata)
        other._default_value = self._default_value
        other._parent = self._parent
        other._cache = copy(self._cache)
        return other

    def __serialize__(self) -> typing.Any: return self._entry.dump()

    @classmethod
    def __deserialize__(cls, *args, **kwargs) -> Node: return cls(*args, **kwargs)

    @property
    def name(self) -> str: return self._metadata.get("name", "unamed")

    @property
    def __units__(self) -> str: return self._metadata.get("units", None)

    def _repr_svg_(self):
        from ..views.View import display
        return display(self, output="svg")

    @property
    def __value__(self) -> _T:
        if self._entry is None or self._entry is _not_found_:
            raise RuntimeError(f"{self} is not a valid value {self.__class__.__name__}")

        if not self._entry.is_generator:
            return self._entry.get(default_value=self._default_value)
        else:
            raise RuntimeError(f"This is a generator, can not return single value! path=\"{self._entry.path}\"")

    def __reduce__(self, *args, **kwargs) -> typing.Any:
        if self._entry is None or self._entry is _not_found_ or not self._entry.is_generator:
            return self.__value__

        value = [v for v in self._entry.find() if v is not None]

        if not isinstance(value, list):
            return value
        else:
            raise NotImplementedError(f"TODO: {value}")

    def __type_hint__(self, key=None) -> typing.Type:
        """ 获取 Container 或 Node 的泛型类型，若没有泛型类型，返回 None
            @NOTE:
             __orig_class__ 和 __orig_base__是非官方支持的API，可能会在未来版本中被删除。

        """
        orig_class = getattr(self, "__orig_class__", None)
        # logger.debug((self.__class__, typing.get_origin(self.__class__), orig_class))
        if orig_class is not None:
            orig_bases = [orig_class]
        else:
            orig_bases = getattr(self, "__orig_bases__", [])

        type_hints = sum([list(typing.get_args(c)) for c in orig_bases], start=[])
        # logger.debug((orig_bases, type_hints))
        if len(type_hints) == 0:
            return None
        else:
            if len(type_hints) > 1:
                logger.warning(f"More than one type hints {type_hints} {self.__class__}")
            return type_hints[-1]

    # def __float__(self): return float(self.__value__)

    # def __bool__(self): return bool(self.__value__)

    def __str__(self): return str(self.__value__)

    def __array__(self): return as_array(self.__value__)

    def __getitem__(self, key) -> Node | _T: return self.__getchild__(key)

    def __setitem__(self, key, value) -> Node | _T: return self.__setchild__(key, value)

    def __delitem__(self, key) -> bool: return self.__delchild__(key) > 0

    def __contains__(self, key) -> bool: return self.__getchild__([Path.tags.count]) > 0

    def __len__(self) -> int: return self._entry.count

    def __iter__(self) -> typing.Generator[typing.Any, None, None]:
        type_hint = self.__type_hint__()

        for v in self._entry.children:
            yield self.as_child(*v, type_hint=type_hint, parent=self)

    # def __equal__(self, other) -> bool: return self._entry.__equal__(other)

    @property
    def _root(self) -> Node | None:
        p = self
        # FIXME: ids_properties is a work around for IMAS dd until we found better solution
        while p._parent is not None and getattr(p, "ids_properties", None) is None:
            p = p._parent
        return p

    def append(self, value) -> Node:
        self._entry.append(value)
        return self

    def insert(self, path, value, **kwargs) -> Node | typing.Any: return self._entry.insert(path, value, **kwargs)

    def get(self, path:  PathLike | Path = None, default_value: typing.Any = _undefined_,  **kwargs) -> typing.Any:
        """ 获取子节点   """

        path = as_path(path)

        value = path.fetch(self._cache, default_value=_not_found_,  **kwargs)

        if value is _not_found_:

            value = self._entry.child(path).fetch(default_value=_not_found_,  **kwargs)

            # if value is not _not_found_:
            #     value = self._as_child(path, value)

        if value is _not_found_:  # 如果没有找到，就返回默认值
            value = default_value

        return value

    def find(self, query: dict | None = None, *args, **kwargs) -> typing.Generator[Node, None, None]:
        entry = self._entry.child(query) if query is not None else self._entry

        for p, v in entry.find():
            yield self.as_child_deep(p, v, *args, **kwargs)

    def as_child(self, key: PathLike,
                 value: typing.Any = _not_found_,
                 default_value: typing.Any = _undefined_,
                 type_hint: typing.Type = _not_found_,
                 parent: Node = None, **kwargs) -> Node | typing.Dict[str, Node] | typing.List[Node]:
        """ 获取子节点   """
        if parent is None:
            parent = self

        if isinstance(key, set):
            return DictProxy[_T]({k: self.as_child(k, default_value=default_value, parent=parent, type_hint=type_hint, **kwargs) for k in key})

        elif isinstance(key, tuple):
            return ListProxy[_T]([self.as_child(k, default_value=default_value,   parent=parent, type_hint=type_hint, **kwargs) for k in key])

        elif isinstance(key, (slice, dict)):
            return ListProxy[_T]([self.as_child(None, v,  default_value=default_value, parent=parent, type_hint=type_hint, **kwargs) for v in self._entry.child(key).find()])

        # elif isinstance(key, dict):
        #     raise NotImplementedError(f"dict {key}")

        if isinstance(key, str):
            if value is _not_found_ or value is None:
                value = self._entry.child(key)

            if type_hint is None or type_hint is _not_found_:
                type_hint = self.__type_hint__(key)

            if default_value is None or default_value is _not_found_:
                if isinstance(self._default_value, collections.abc.Mapping):
                    default_value = self._default_value.get(key, _not_found_)
                else:
                    default_value = self._default_value

        else:
            type_hint = self.__type_hint__()

            default_value = self._default_value

            if (value is _not_found_ or value is None) and (key is not None and key is not _not_found_):
                value = self._entry.child(key)

        origin_class = typing_get_origin(type_hint)

        # else:
        #     raise KeyError(f"{key} not found")

        if inspect.isclass(origin_class) and isinstance(value, origin_class):
            pass
        elif inspect.isclass(origin_class) and issubclass(origin_class, Node):
            value = type_hint(value, default_value=default_value,  parent=parent, **kwargs)
        else:
            if isinstance(value, Entry):
                value = value.__value__

            if value is None or value is _not_found_:
                value = default_value

            if value is None or value is _not_found_:
                pass

            elif not inspect.isclass(origin_class):
                if not isinstance(value, primary_type):
                    value = Node(value, parent=parent)

            elif isinstance(value, origin_class):
                pass

            elif issubclass(origin_class, array_type):
                value = as_array(value)

            elif type_hint in primary_type:
                value = type_hint(value)

            elif dataclasses.is_dataclass(type_hint):
                value = as_dataclass(type_hint, value)

            elif issubclass(type_hint, Enum):
                if isinstance(value, collections.abc.Mapping):
                    value = type_hint[value["name"]]
                elif isinstance(value, str):
                    value = type_hint[value]
                else:
                    raise TypeError(f"Can not convert {value} to {type_hint}")

            elif callable(type_hint):
                value = type_hint(value)

            else:
                raise TypeError(f"Can not convert {value} to {type_hint}")

        return value

    def as_child_deep(self, path:  PathLike | Path | None = None, value=None,
                      default_value: typing.Any = _not_found_, **kwargs) -> Node:
        """
            将 value 转换为 Node
            ----
            Parameters:
                - obj: 任意类型的数据
                - type_hint: 将obj转换到目标类型
                - path: child在obj中的路径
                - default_value: 默认值
                - kwargs: 其他参数
            若 obj 为 Node，调用 obj.get(path, **kwargs)
            当 type_hint 为 None 时，将 obj 转换为 entry
            当 type_hint 不为 None 时，根据 path 获得 obj 的子节点（as entry）， 根据 path 从 type_hint 中获取子类型，
        """

        path = Path(path)

        if len(path) == 0:
            return self

        parent = self._parent

        obj = self

        for idx, key in enumerate(path[:]):

            if obj is None or obj is _not_found_:
                break
            elif not isinstance(obj, Node):
                obj = as_entry(obj).child(path[idx:])
                if isinstance(parent, Node):
                    obj = parent.as_child(key, obj, default_value=default_value, **kwargs)
                else:
                    obj = Node(obj,  default_value=default_value, **kwargs)

            if key == Path.tags.root:
                obj = obj._root
                parent = None
                continue
            elif key is Path.tags.parent:
                obj = obj._parent
                parent = None
                continue
            # elif key == "*":
            #     key = slice(None)

            parent = obj

            if idx < len(path)-1:
                obj = obj.as_child(key, **kwargs)
            else:
                obj = obj.as_child(key, value, default_value=default_value, **kwargs)
        # else:
        #     # obj = default_value
        #     logger.debug(f"Canot find {path[:idx]} {idx} in {self}")
        # if obj is _not_found_ or obj is None:
        #     obj = default_value

        return obj

        #    return value
        # if type_hint is None or type_hint is _not_found_:
        #     # 当 type_hint 为 None 时，，尽可能返回 raw value
        #     if isinstance(value, Entry):  # 若 value 为 entry，获得其 __value__
        #         value = value.__value__
        #     elif value is None or value is _not_found_:  # 若为 None，零七位 default_value
        #         value = default_value

        #     if isinstance(value, primary_type):  # 若 value 为 primary_type, 直接返回
        #         return value
        #     else:  # 否则转换为 Node
        #         return Node(value, default_value=default_value, **kwargs)

        # def get_child_by_key(obj: Node, path: list, type_hint=None, default_value=_not_found_, parent=None, **kwargs) -> Node:

        #     path = Path(path)

        #     if not isinstance(obj, Node):
        #         return as_node(as_entry(obj, path=path), type_hint=type_hint,
        #                        defalut_value=default_value, parent=parent, **kwargs)

        # def _validate(self, value, type_hint) -> bool:
        #     if value is _undefined_ or type_hint is _undefined_:
        #         return False
        #     else:
        #         v_orig_class = getattr(value, "__orig_class__", value.__class__)

        #         if inspect.isclass(type_hint) and inspect.isclass(v_orig_class) and issubclass(v_orig_class, type_hint):
        #             res = True
        #         elif typing.get_origin(type_hint) is not None \
        #                 and typing.get_origin(v_orig_class) is typing.get_origin(type_hint) \
        #                 and typing.get_args(v_orig_class) == typing.get_args(type_hint):
        #             res = True
        #         else:
        #             res = False
        #     return res

        # def _as_child(self, key: str, value=_not_found_,  *args, **kwargs) -> Node:
        #     raise NotImplementedError("as_child")

    def __getchild__(self, key: PathLike,
                     getter: typing.Callable[..., typing.Any] | None = None,
                     default_value: typing.Any = _undefined_,
                     type_hint: typing.Type = _not_found_,
                     **kwargs) -> Node | _T:
        """ 获取子节点   """

        if isinstance(key, (list, tuple)):
            raise TypeError(f"__getchild__ do not support {key}")

        elif isinstance(key, set):
            if default_value is _not_found_:
                default_value = self._default_value

            return DictProxy[_T]({
                k: self.__getchild__(k,
                                     default_value=default_value.get(k, _not_found_) if isinstance(
                                         default_value, collections.abc.Mapping) else default_value,
                                     parent=self) for k in key})

        elif isinstance(key, (slice, dict)):
            if default_value is _not_found_:
                default_value = self._default_value

            return ListProxy[_T](self._entry, cache=self._cache, default_value=default_value, query=key, parent=self)

        elif isinstance(key, str):

            value = self._cache.get(key, _not_found_)

            if value is not _not_found_:
                pass
            elif callable(getter):
                value = getter(self)
            else:
                value = self._entry.child(key)

            if type_hint is None or type_hint is _not_found_:
                type_hint = self.__type_hint__(key)

            if default_value is None or default_value is _not_found_:
                if isinstance(self._default_value, collections.abc.Mapping):
                    default_value = self._default_value.get(key, _not_found_)
                else:
                    default_value = self._default_value

        else:
            type_hint = self.__type_hint__()

            default_value = self._default_value

            value = self._entry.child(key)

        res = self._as_child(value, type_hint, default_value=default_value, parent=self, **kwargs)

        if isinstance(key, (int, str)):
            self._cache[key] = res

        return res

    def _as_child(self, value, type_hint: typing.Type, default_value: typing.Any = _not_found_, **kwargs) -> Node | PrimaryType:

        origin_class = typing_get_origin(type_hint)

        if inspect.isclass(origin_class) and isinstance(value, origin_class):
            pass

        elif inspect.isclass(origin_class) and issubclass(origin_class, Node):
            value = type_hint(value, default_value=default_value, **kwargs)

        elif isinstance(value, Entry):
            value = self._as_child(value.__value__, type_hint=type_hint, default_value=default_value, **kwargs)

        else:
            if value is None or value is _not_found_:
                value = default_value

            if value is None or value is _not_found_:
                pass

            elif not inspect.isclass(origin_class):
                if not isinstance(value, primary_type):
                    value = Node(value,  default_value=default_value, **kwargs)

            elif isinstance(value, origin_class):
                pass

            elif issubclass(origin_class, array_type):
                value = as_array(value)

            elif type_hint in primary_type:
                value = type_hint(value)

            elif dataclasses.is_dataclass(type_hint):
                value = as_dataclass(type_hint, value)

            elif issubclass(type_hint, Enum):
                if isinstance(value, collections.abc.Mapping):
                    value = type_hint[value["name"]]
                elif isinstance(value, str):
                    value = type_hint[value]
                else:
                    raise TypeError(f"Can not convert {value} to {type_hint}")

            elif callable(type_hint):
                value = type_hint(value)

            else:
                raise TypeError(f"Can not convert {value} to {type_hint}")

        return value


class DictProxy(Node[_T]):

    def __getitem__(self, path: PathLike) -> typing.Any:
        return Path(path).fetch(self)

    def __getattr__(self, name: str) -> typing.Any:
        return super().__getitem__(name)


class ListProxy(Node[_T]):
    def __init__(self, *args, default_value=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._default_value = default_value

    def __getitem__(self, path: PathLike) -> typing.Any: return self._get(Path(path))

    def __getattr__(self, name: str) -> typing.Any: return self._get(Path([name]))
    # default_value = self._default_value.get(name, None) if self._default_value is not None else None
    # return ListProxy([(getattr(obj, name, None) if not isinstance(obj, Node) else obj.get(name, default_value=default_value)) for obj in self])

    def _get(self, path: Path) -> typing.Any:
        raise KeyError(path)

    @property
    def __value__(self): return [getattr(obj, "__value__", obj) for obj in self]

    def __reduce__(self, op=None) -> typing.Any:
        res = [obj for obj in self if obj is not None]
        if len(res) == 0:
            return None
        elif len(res) == 1:
            return res[0]

        elif op is not None:
            return op(res)

        elif isinstance(res[0], np.ndarray):
            return np.sum(res)

        else:
            return res[0]
