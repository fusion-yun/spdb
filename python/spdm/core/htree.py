""" Hierarchical Tree (HTree) is a hierarchical data structure that can be used to
 store a group of data or objects, such as lists, dictionaries, etc.  """

from __future__ import annotations
import collections.abc
import typing
from copy import deepcopy
import numpy as np

from spdm.utils.logger import logger
from spdm.utils.misc import get_positional_argument_count
from spdm.utils.tags import _not_found_, _undefined_
from spdm.utils.typing import (
    ArrayType,
    as_array,
    isinstance_generic,
    type_convert,
)

from spdm.core.entry import Entry, open_entry
from spdm.core.path import Path, PathLike, as_path
from spdm.core.generic_helper import GenericHelper


def get_state(obj: typing.Any) -> dict:
    if hasattr(obj.__class__, "__getstate__"):
        return obj.__getstate__()
    elif isinstance(obj, collections.abc.Mapping):
        return {k: get_state(v) for k, v in obj.items()}
    elif isinstance(obj, collections.abc.Sequence) and not isinstance(obj, str):
        return [get_state(v) for v in obj]
    else:
        return obj


class HTreeNode:
    """HTreeNode is a node in the hierarchical tree."""

    def __new__(cls, *args, **kwargs):
        if cls is not HTreeNode or len(args) != 1:
            return super().__new__(cls)
        elif len(args) == 0:
            return Dict(**kwargs)
        elif len(args) > 1:
            return List(*args, **kwargs)

        value = args[0]

        if isinstance(value, HTreeNode):
            return value
        elif isinstance(value, collections.abc.Mapping):
            return Dict(value, **kwargs)
        elif isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
            return List(value, **kwargs)
        else:
            return value

    def __init__(self, cache: typing.Any = _not_found_, /, _entry: Entry = None, _parent: HTreeNode = None, **metadata):
        """Initialize a HTreeNode object."""
        self._cache = cache
        self._entry = open_entry(_entry)
        self._parent = _parent
        self._metadata = metadata

    @property
    def is_leaf(self) -> bool:
        """只读属性，返回节点是否为叶节点"""
        return True

    @property
    def is_sequence(self) -> bool:
        """只读属性，返回节点是否为Sequence"""
        return False

    @property
    def is_mapping(self) -> bool:
        """只读属性，返回节点是否为Mapping"""
        return False

    def __getstate__(self) -> dict:

        state = {
            "$type": f"{self.__class__.__module__}.{self.__class__.__name__}",
            "$path": ".".join(self.__path__),
            "$name": self.__name__,
            "$entry": self._entry.__getstate__(),
            "$metadata": self._metadata,
        }

        if isinstance(self._cache, collections.abc.Mapping):
            state.update(get_state(self._cache))
        else:
            state["$data"] = get_state(self._cache)

        return state

    def __setstate__(self, state: dict) -> None:

        self._entry = open_entry(state.pop("$entry", None))
        self._metadata = state.pop("$metadata", {})

        logger.verbose(f"Load {self.__class__.__name__} from state: {state.pop('$type',None)}")

        self._cache = state.pop("$data", _not_found_)

        if self._cache is _not_found_:
            self._cache = state
        elif len(state) > 0:
            logger.warning(f"Ignore property {list(state.keys())}")

    # def __copy__(self) -> typing.Self:
    #     if isinstance(self._cache, dict):
    #         cache = {k: copy(value) for k, value in self._cache.items()}
    #     elif isinstance(self._cache, list):
    #         cache = [copy(value) for k, value in self._cache.items()]
    #     else:
    #         cache = deepcopy(self._cache)

    #     res = self.__class__(cache, _entry=self._entry)

    #     res._metadata = deepcopy(self._metadata)

    #     return res

    # @classmethod
    # def do_serialize(cls, source: typing.Any, dumper: Entry | typing.Callable[..., typing.Any] | bool) -> _T:
    #     if source is _not_found_:
    #         return source if not isinstance(dumper, Entry) else dumper

    #     elif hasattr(source.__class__, "__serialize__"):
    #         return source.__serialize__(dumper)

    #     elif isinstance(source, dict):
    #         if isinstance(dumper, Entry):
    #             for k, v in source.items():
    #                 cls.do_serialize(v, dumper.child(k))
    #             res = dumper
    #         else:
    #             res = {k: cls.do_serialize(v, dumper) for k, v in source.items()}

    #     elif isinstance(source, list):
    #         if isinstance(dumper, Entry):
    #             for k, v in enumerate(source):
    #                 cls.do_serialize(v, dumper.child(k))
    #             res = dumper
    #         else:
    #             res = [cls.do_serialize(v, dumper) for v in source]

    #     elif isinstance(dumper, Entry):
    #         dumper.insert(source)
    #         res = dumper

    #     elif callable(dumper):
    #         res = dumper(source)

    #     elif dumper is True:
    #         res = deepcopy(source)

    #     else:
    #         res = source

    #     return res

    # def __serialize__(self, dumper: Entry | typing.Callable[..., typing.Any] | bool = True) -> Entry | typing.Any:
    #     """若 dumper 为 Entry，将数据写入 Entry
    #        若 dumper 为 callable，将数据传入 callable 并返回结果
    #        若 dumper 为 True，返回数据的拷贝
    #        否则返回序列化后的数据

    #     Args:
    #         target (Entry, optional): 目标入口. Defaults to None.
    #         copier (typing.Callable[[typing.Any], typing.Any] | bool, optional): copier 拷贝器，当 target 为 None 有效。若为 True 则通过 copy 函数返回数据的拷贝. Defaults to None.

    #     Returns:
    #         typing.Any: 若 target is None，返回原始数据，否则返回 target
    #     """
    #     if self._cache is _not_found_:
    #         if self._entry is not None:
    #             return self._entry.dump(dumper)
    #         else:
    #             return self.do_serialize(self.__value__, dumper)
    #     else:
    #         return self.do_serialize(self._cache, dumper)

    # @classmethod
    # def __deserialize__(cls, *args, **kwargs) -> typing.Type[HTree]:
    #     return cls(*args, **kwargs)

    # def __duplicate__(self, *args, _parent=_not_found_, **kwargs):
    #     if _parent is _not_found_:
    #         _parent = self._parent

    #     cls = get_type(self)

    #     if len(args) == 0:
    #         args = [deepcopy(self._cache)]

    #     return cls(
    #         *args,
    #         _parent=_parent,
    #         _entry=self._entry,
    #         **collections.ChainMap(kwargs, deepcopy(self._metadata)),
    #     )

    @property
    def __name__(self) -> str:
        return self._metadata.get("name", self.__class__.__name__)

    @property
    def __path__(self) -> typing.List[str | int]:
        if isinstance(self._parent, HTreeNode):
            return self._parent.__path__ + [self.__name__]
        else:
            return [self.__name__]

    @property
    def __label__(self) -> str:
        return self._metadata.get("label", None) or ".".join(self.__path__)

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} name='{'.'.join(self.__path__)}' />"

    def __repr__(self) -> str:
        return ".".join(self.__path__)

    @property
    def __root__(self) -> HTree | None:
        p = self
        while isinstance(p, HTreeNode) and p._parent is not None:
            p = p._parent
        return p

    @property
    def __value__(self) -> typing.Any:
        return self._cache

    def __array__(self) -> ArrayType:  # for numpy
        return as_array(self.__value__)

    def __null__(self) -> bool:
        """判断节点是否为空，若节点为空，返回 True，否则返回 False
        @NOTE 长度为零的 list 或 dict 不是空节点
        """
        return self._cache is None and self._entry is None

    def __empty__(self) -> bool:
        return (self._cache is _not_found_ or len(self._cache) == 0) and (self._entry is None)

    def __bool__(self) -> bool:
        return self.__null__() or self.__empty__() or bool(self.__value__)

    def __equal__(self, other) -> bool:
        if isinstance(other, HTreeNode):
            return other.__equal__(self._cache)
        else:
            return self._cache == other

    def fetch(self):
        """fetch data from  entry to cache"""
        if self._entry is not None:
            self._cache.update(self._entry.dump())
        return self

    def flush(self):
        """flush data from cache to entry"""
        if self._entry is not None:
            self._entry.update(self._cache)
        return self


null_node = HTreeNode(_not_found_)


_T = typing.TypeVar("_T")


class HTree(GenericHelper[_T], HTreeNode):
    """Hierarchical Tree:
    - 其成员类型为 _T，用于存储一组数据或对象，如列表，字典等

    - 一种层次化的数据结构，它具有以下特性：
    - 树节点也可以是列表 list，也可以是字典 dict
    - 叶节点可以是标量或数组 array_type，或其他 type_hint 类型
    - 节点可以有缓存（cache)
    - 节点可以有父节点（_parent)
    - 节点可以有元数据（metadata)
    - 任意节点都可以通过路径访问
    - `get` 返回的类型由 `type_hint` 决定，默认为 Node
    """

    @property
    def is_leaf(self) -> bool:
        """只读属性，返回节点是否为叶节点"""
        return False

    def __equal__(self, other) -> bool:
        """TODO: 判断两个容器/树是否相等
        O(N) 操作需要优化方法
        """
        raise NotImplementedError(f"{self.__class__.__name__}.__equal__ is not implemented!")

    # 对后辈节点操作，支持路径

    @typing.final
    def put(self, path, value, *args, **kwargs):
        """put value to path"""
        return as_path(path).update(self, value, *args, **kwargs)

    @typing.final
    def get(self, path: PathLike, default_value: _T = _undefined_, **kwargs) -> _T:
        """get value from path"""
        value = as_path(path).find(self, default_value=default_value, **kwargs)
        if value is _undefined_:
            raise KeyError(f"Can not find value at path {path}!")
        return value

    @typing.final
    def pop(self, path, default_value=_not_found_):
        """pop value from path"""
        path = as_path(path)

        value = path.get(self, _not_found_)

        if value is not _not_found_:
            path.put(self, _not_found_)
            return value
        else:
            return default_value

    @typing.final
    def __getitem__(self, path) -> _T:
        value = self.get(path, default_value=_not_found_)
        return value if value is not _not_found_ else self.__missing__(path)

    @typing.final
    def __setitem__(self, path, value) -> None:
        self.put(path, value, Path.tags.overwrite)

    @typing.final
    def __delitem__(self, path) -> None:
        return self.put(path, _not_found_, _idempotent=True)

    def __missing__(self, key: str | int) -> typing.Any:
        # raise KeyError(f"{self.__class__.__name__}.{key} is not assigned! ")
        return _not_found_

    # 当前子节点操作，不支持路径

    def __iter__(self) -> typing.Generator[_T | str, None, None]:
        """遍历，sequence 返回子节点的值，mapping 返回子节点的键"""
        yield from self.for_each()

    @typing.final
    def __contains__(self, key_or_node) -> bool:
        """查找，sequence 搜索值，mapping搜索键"""
        return self.find(key_or_node, Path.tags.exists)

    @typing.final
    def __len__(self) -> int:
        return int(self.find(None, Path.tags.count) or 0)

    # RESTful API

    @typing.final
    def insert(self, *args, **kwargs) -> None:
        """insert value"""
        return self._insert_(*args, **kwargs)

    @typing.final
    def update(self, *args, **kwargs) -> None:
        """update value"""
        if len(args) == 0 or isinstance(args[0], dict):
            args = tuple(None, *args)
        return self._update_(*args, **kwargs)

    @typing.final
    def remove(self, *args, **kwargs) -> bool:
        """remove value"""
        return self._remove_(*args, **kwargs)

    @typing.final
    def find(self, *args, **kwargs) -> _T:
        """find value"""
        return self._find_(*args, **kwargs)

    @typing.final
    def for_each(self, *args, **kwargs) -> typing.Generator[_T, None, None]:
        """iterate children"""
        yield from self._for_each_(*args, **kwargs)

    @typing.final
    def children(self) -> typing.Generator[_T, None, None]:
        """alias of for_each"""
        yield from self.for_each()

    @typing.final
    def find_cache(self, path, *args, default_value=_not_found_, **kwargs) -> typing.Any:
        """find value from cache"""
        res = Path.do_find(self._cache, path, *args, default_value=_not_found_, **kwargs)
        if res is _not_found_ and self._entry is not None:
            res = self._entry.child(path).find(*args, default_value=_not_found_, **kwargs)
        if res is _not_found_:
            res = default_value
        return res

    @typing.final
    def get_cache(self, path, default_value=_not_found_) -> typing.Any:
        """get value from cache"""
        return self.find_cache(path, default_value=default_value)

    ################################################################################
    # Protected methods

    def _insert_(self, value: typing.Any, *args, **kwargs):
        """插入节点："""
        return self._update_(None, value, Path.tags.insert, *args, **kwargs)

    def _remove_(self, key: str | int, *args, _deleter: typing.Callable = None, **kwargs) -> bool:
        """删除节点：
        - 将 _cahce 中 path 对应的节点设置为 None，这样访问时不会触发 _entry
        - 若 path 为 None，删除所有子节点
        """
        if callable(_deleter):
            return _deleter(self, key)
        else:
            return self._update_(key, _not_found_, Path.tags.remove, *args, **kwargs)

    def _update_(self, key: str | int, value: typing.Any, *args, _setter=None, **kwargs):
        """更新节点："""
        if (key is None or key == []) and value is self:
            pass

        elif isinstance(key, str) and key.startswith("@"):
            value = Path.do_update(self._metadata, key[1:], value, *args, **kwargs)
            if value is not _not_found_:
                return value

        elif callable(_setter):
            _setter(self, key, value)

        else:
            self._cache = Path.do_update(self._cache, key, value, *args, **kwargs)

        return self

    def _find_(self, key, *args, _getter=None, default_value=_not_found_, **kwargs) -> _T:
        """获取子节点/或属性
        搜索子节点的优先级  cache > getter > entry > default_value
        当 default_value 为 _not_found_ 时，若 cache 中找不到节点，则从 entry 中获得

        """

        if isinstance(key, str) and key.startswith("@"):
            return Path.do_find(self._metadata, key[1:], *args, default_value=_not_found_)

        if isinstance(key, int):
            if key < len(self._cache):
                value = self._cache[key]
            else:
                value = _not_found_
        else:
            value = Path.do_find(self._cache, key, default_value=_not_found_)

        if value is _not_found_ and callable(_getter):
            if get_positional_argument_count(_getter) == 2:
                value = _getter(self, key)
            else:
                value = _getter(self)

        _entry = self._entry.child(key) if self._entry is not None else None

        value = self._type_convert(value, key, _entry=_entry, default_value=default_value, **kwargs)

        if key is None and isinstance(self._cache, collections.abc.MutableSequence):
            self._cache.append(value)
        elif isinstance(key, str) and isinstance(self._cache, collections.abc.MutableSequence):
            self._cache = Path.do_update(self._cache, key, value)
        elif isinstance(key, int) and key <= len(self._cache):
            if self._cache is _not_found_:
                self._cache = []
            self._cache.extend([_not_found_] * (key - len(self._cache) + 1))
            self._cache[key] = value
        else:
            if not isinstance(self._cache, collections.abc.Mapping):
                self._cache = {}
            self._cache[key] = value

        return value

    def _for_each_(self, *args, **kwargs) -> typing.Generator[str | _T, None, None]:

        if (self._cache is _not_found_ or len(self._cache) == 0) and self._entry is not None:
            for k, v in self._entry.for_each(*args, **kwargs):
                if not isinstance(v, Entry):
                    yield k, self._type_convert(v, k)
                else:
                    yield k, self._type_convert(_not_found_, k, _entry=v)

        elif self._cache is not None:
            for k, v in Path.do_for_each(self._cache, [], *args, **kwargs):
                _entry = self._entry.child(k) if self._entry is not None else None
                v = self._type_convert(v, k, _entry=_entry)
                yield k, v

    # -----------------------------------------------------------------------------
    # Private methods

    def _type_hint_(self, key: str | int = None) -> typing.Type:
        """当 key 为 None 时，获取泛型参数，若非泛型类型，返回 None，
        当 key 为字符串时，获得属性 property 的 type_hint
        """

        if isinstance(key, str) and key.startswith("@"):
            return None

        tp = None

        if isinstance(key, str):
            cls = getattr(self, "__orig_class__", self.__class__)

            tp = typing.get_type_hints(typing.get_origin(cls) or cls).get(key, None)

        if tp is None:
            tp = getattr(self.__class__, "__args__", [])
            # get_args(getattr(self, "__orig_class__", None) or self.__class__)
            tp = tp[-1] if len(tp) > 0 else None

        return tp

    def _type_convert(
        self,
        value: typing.Any,
        _key: int | str,
        default_value: typing.Any = _not_found_,
        _type_hint: typing.Type = None,
        _entry: Entry | None = None,
        _parent: HTree | None = None,
        **kwargs,
    ) -> _T:
        if _type_hint is None:
            _type_hint = self._type_hint_(_key)

        if value is not _not_found_:
            pass
        elif _entry is not None:
            value = _entry.get(default_value=default_value)
            _entry = None
            default_value = _not_found_
        else:
            value = default_value

        if _type_hint is None:
            return value

        if _parent is None:
            _parent = self

        if isinstance_generic(value, _type_hint):
            pass
        elif issubclass(typing.get_origin(_type_hint) or _type_hint, HTree):
            value = _type_hint(value, _entry=_entry, _parent=_parent, **kwargs)
        else:
            value = type_convert(_type_hint, value, **kwargs)

        if isinstance(value, HTreeNode):
            if value._parent is None and _parent is not _not_found_:
                value._parent = _parent

            if len(kwargs) > 0:
                value._metadata.update(kwargs)

            if isinstance(_key, str):
                value._metadata["name"] = _key

            elif isinstance(_key, int):
                value._metadata.setdefault("index", _key)
                if self._metadata.get("name", _not_found_) in (_not_found_, None, "unnamed"):
                    self._metadata["name"] = str(_key)

        return value


# def as_htree(*args, **kwargs):
#     """将数据转换为 HTree 对象"""
#     if len(args) == 0 and len(kwargs) > 0:
#         res = Dict(kwargs)
#         kwargs = {}
#     elif len(args) > 1 and len(kwargs) == 0:
#         res = List(list(args))
#         args = []
#     elif len(args) == 0:
#         res = None
#     elif isinstance(args[0], HTree):
#         res = args[0]
#         args = args[1:]
#     elif isinstance(args[0], collections.abc.MutableMapping):
#         res = Dict(args[0])
#         args = args[1:]
#     elif isinstance(args[0], collections.abc.MutableSequence):
#         res = List(args[0])
#         args = args[1:]
#     elif len(args) > 1:
#         res = List(list(args))
#         args = []
#     else:
#         res = HTree(*args, **kwargs)

#     if len(args) + len(kwargs) > 0:
#         res._update_(*args, **kwargs)

#     return res


class Dict(HTree[_T]):
    """Dict 类型的 HTree 对象"""

    def __init__(self, cache: typing.Any = _not_found_, /, _entry: Entry = None, _parent: HTreeNode = None, **kwargs):
        if cache is _not_found_:
            cache = kwargs
            kwargs = {}
        super().__init__(cache, _entry=_entry, _parent=_parent, **kwargs)

    @property
    def is_mapping(self) -> bool:
        """只读属性，返回节点是否为Mapping"""
        return True

    def __equal__(self, other) -> bool:
        return False
        # raise NotImplementedError(f"{self.__class__.__name__}.__equal__ is not implemented!")

    @typing.final
    def __iter__(self) -> typing.Generator[str, None, None]:
        """遍历，sequence 返回子节点的值，mapping 返回子节点的键"""
        yield from self.keys()

    def items(self) -> typing.Generator[typing.Tuple[str, _T], None, None]:
        """遍历 key,value"""
        yield from self.for_each(only_key=False, only_value=False)

    def keys(self) -> typing.Generator[str, None, None]:
        """遍历 key"""
        yield from self.for_each(only_key=True)

    def values(self) -> typing.Generator[_T, None, None]:
        """遍历 value"""
        yield from self.for_each(only_value=True)


collections.abc.MutableMapping.register(Dict)


class List(HTree[_T]):
    """List 类型的 HTree 对象"""

    def __init__(self, *args, **kwargs):
        if len(args) != 1:
            args = (list[args],)
        super().__init__(*args, **kwargs)

    @property
    def is_sequence(self) -> bool:
        """只读属性，返回节点是否为 Sequence"""
        return True

    def __equal__(self, other) -> bool:
        raise NotImplementedError(f"{self.__class__.__name__}.__equal__ is not implemented!")

    def append(self, value):
        """append value to list"""
        return self.insert(value, Path.tags.append)

    def extend(self, value):
        """extend value to list"""
        return self.insert(value, Path.tags.extend)

    def __iadd__(self, other: list) -> typing.Type[List[_T]]:
        return self.extend(other)


collections.abc.MutableSequence.register(List)
