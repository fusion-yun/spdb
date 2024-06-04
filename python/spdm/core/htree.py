from __future__ import annotations
import collections.abc
import abc
import typing
import numpy as np
from copy import copy, deepcopy

from ..utils.logger import logger


from ..utils.misc import get_positional_argument_count
from ..utils.tags import _not_found_
from ..utils.typing import (
    ArrayType,
    NumericType,
    array_type,
    as_array,
    get_args,
    get_origin,
    isinstance_generic,
    numeric_type,
    serialize,
    get_type,
    type_convert,
)

from .entry import Entry, open_entry
from .path import Path, PathLike, Query, as_path, update_tree, merge_tree, path_like


class HTreeNode:
    @classmethod
    def _parser_args(cls, *args, _parent=None, _entry=None, **kwargs):

        if len(args) == 0:
            _cache = _not_found_
        elif isinstance(args[0], (np.ndarray,int,float,complex)):
            _cache = args[0]
            args = args[1:]
        elif isinstance(args[0], (collections.abc.MutableMapping, collections.abc.MutableSequence)):
            _cache = args[0]
            args = args[1:]
        elif isinstance(args[0], (str, Entry)):
            _cache = {"$entry": args[0]}
            args = args[1:]
        else:
            _cache = _not_found_

        if _entry is None:
            _entry = []
        elif not isinstance(_entry, collections.abc.Sequence) or isinstance(_entry, str):
            _entry = [_entry]

        _entry = list(args) + _entry

        metadata = deepcopy(getattr(cls, "_metadata", {}))

        if isinstance(_cache, dict):
            t_entry = _cache.pop("$entry", _not_found_)
            if t_entry is _not_found_:
                pass
            elif t_entry is False:
                _entry = None
            elif not isinstance(t_entry, list):
                _entry = [t_entry] + _entry
            else:
                _entry = t_entry + _entry

            # for k in list(_cache.keys()):
            #     if k.startswith("@"):
            #         metadata[k[1:]] = _cache.pop(k)

        metadata.update(kwargs)

        if not isinstance(_entry, list):
            raise RuntimeError(f"Can not parser _entry {_entry}")

        _entry = open_entry(
            sum([e if isinstance(e, list) else [e] for e in _entry if e is not None and e is not _not_found_], [])
        )

        default_value = metadata.pop("default_value", _not_found_)

        if default_value is not _not_found_:
            _cache = update_tree(deepcopy(default_value), _cache)

        return _cache, _entry, _parent, metadata

    def __init__(self, *args, **metadata) -> None:
        self._cache, self._entry, self._parent, self._metadata = self.__class__._parser_args(*args, **metadata)

    def __copy__(self) -> typing.Self:
        if isinstance(self._cache, dict):
            cache = {k: copy(value) for k, value in self._cache.items()}
        elif isinstance(self._cache, list):
            cache = [copy(value) for k, value in self._cache.items()]
        else:
            cache = deepcopy(self._cache)

        res = self.__class__(cache, _entry=self._entry)

        res._metadata = deepcopy(self._metadata)

        return res

    @classmethod
    def _do_serialize(cls, source: typing.Any, dumper: Entry | typing.Callable[..., typing.Any] | bool) -> _T:
        if source is _not_found_:
            return source if not isinstance(dumper, Entry) else dumper

        elif hasattr(source.__class__, "__serialize__"):
            return source.__serialize__(dumper)

        elif isinstance(source, dict):
            if isinstance(dumper, Entry):
                for k, v in source.items():
                    cls._do_serialize(v, dumper.child(k))
                res = dumper
            else:
                res = {k: cls._do_serialize(v, dumper) for k, v in source.items()}

        elif isinstance(source, list):
            if isinstance(dumper, Entry):
                for k, v in enumerate(source):
                    cls._do_serialize(v, dumper.child(k))
                res = dumper
            else:
                res = [cls._do_serialize(v, dumper) for v in source]

        elif isinstance(dumper, Entry):
            dumper.insert(source)
            res = dumper

        elif callable(dumper):
            res = dumper(source)

        elif dumper is True:
            res = deepcopy(source)

        else:
            res = source

        return res

    def __serialize__(self, dumper: Entry | typing.Callable[..., typing.Any] | bool = True) -> Entry | typing.Any:
        """若 dumper 为 Entry，将数据写入 Entry
           若 dumper 为 callable，将数据传入 callable 并返回结果
           若 dumper 为 True，返回数据的拷贝
           否则返回序列化后的数据

        Args:
            target (Entry, optional): 目标入口. Defaults to None.
            copier (typing.Callable[[typing.Any], typing.Any] | bool, optional): copier 拷贝器，当 target 为 None 有效。若为 True 则通过 copy 函数返回数据的拷贝. Defaults to None.

        Returns:
            typing.Any: 若 target is None，返回原始数据，否则返回 target
        """
        if self._cache is _not_found_:
            if self._entry is not None:
                return self._entry.dump(dumper)
            else:
                return self._do_serialize(self.__value__, dumper)
        else:
            return self._do_serialize(self._cache, dumper)

    @classmethod
    def __deserialize__(cls, *args, **kwargs) -> typing.Type[HTree]:
        return cls(*args, **kwargs)

    def __duplicate__(self, *args, _parent=_not_found_, **kwargs):
        if _parent is _not_found_:
            _parent = self._parent

        cls = get_type(self)

        if len(args) == 0:
            args = [deepcopy(self._cache)]

        return cls(
            *args,
            _parent=_parent,
            _entry=self._entry,
            **collections.ChainMap(kwargs, deepcopy(self._metadata)),
        )

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
        # FIXME: ids_properties is a work around for IMAS dd until we found better solution
        while isinstance(p, HTreeNode) and getattr(p, "ids_properties", None) is None:
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

    @staticmethod
    def _do_fetch(obj, *args, **kwargs):
        if hasattr(obj.__class__, "fetch"):
            return obj.fetch(*args, **kwargs)

        elif isinstance(obj, dict):
            return {k: HTreeNode._do_fetch(v, *args, **kwargs) for k, v in obj.items()}

        elif isinstance(obj, (list, set, tuple)):
            return obj.__class__([HTreeNode._do_fetch(v, *args, **kwargs) for v in obj])

        elif callable(obj):
            return obj(*args, **kwargs)

        else:
            return deepcopy(obj)

            # raise RuntimeError(f"Unknown argument {obj} {args} {kwargs}")

    def fetch(self, *args, **kwargs) -> typing.Self:
        return self.__duplicate__(HTreeNode._do_fetch(self._cache, *args, **kwargs))

    def flush(self):
        """TODO: 将 cache 内容 push 入 entry"""
        return NotImplemented


null_node = HTreeNode(_not_found_)


_T = typing.TypeVar("_T")


class HTree(HTreeNode, typing.Generic[_T]):
    """Hierarchical Tree:
    - 其成员类型为 _T，用于存储一组数据或对象，如列表，字典等

    - 一种层次化的数据结构，它具有以下特性：
    - 树节点也可以是列表 list，也可以是字典 dict
    - 叶节点可以是标量或数组 array_type，或其他 type_hint 类型
    - 节点可以有缓存（cache)
    - 节点可以有父节点（_parent)
    - 节点可以有元数据（metadata), 包含： 唯一标识（id), 名称（name), 单位（units), 描述（description), 标签（tags), 注释（comment)
    - 任意节点都可以通过路径访问
    - `get` 返回的类型由 `type_hint` 决定，默认为 Node



    """

    def __contains__(self, path) -> bool:
        return bool(self.get(path, Path.tags.exists)) is True

    #############################################
    # 对后辈节点操作，支持路径

    def put(self, path, value, *args, **kwargs):
        return as_path(path).update(self, value, *args, **kwargs)

    def get(self, path: PathLike, default_value: _T = _not_found_, *args, **kwargs) -> _T:
        return as_path(path).find(self, *args, default_value=default_value, **kwargs)

    @typing.final
    def pop(self, path, default_value=_not_found_):
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

    @typing.final
    def get_cache(self, path, default_value: _T = _not_found_) -> _T:
        path = as_path(path)
        res = path.get(self._cache, default_value=_not_found_)

        if res is _not_found_ and self._entry is not None:
            res = self._entry.get(path, _not_found_)

        if res is _not_found_:
            res = default_value

        return res

    #############################################
    # 当子节点操作，不支持路径
    @abc.abstractclassmethod
    def children(self) -> typing.Generator[_T, None, None]:
        """alias of for_each"""
        return

    @abc.abstractclassmethod
    def __iter__(self) -> typing.Generator[_T | str, None, None]:
        """遍历 children"""
        return

    @typing.final
    def __len__(self) -> int:
        return int(self._find_(None, Path.tags.count) or 0)

    @typing.final
    def __contains__(self, key) -> bool:
        return bool(self.find(key, Path.tags.exists) is True)

    @typing.final
    def __equal__(self, other) -> bool:
        return bool(self._find_(None, Path.tags.equal, other))

    ###############################################################################
    # RESTful API

    @typing.final
    def insert(self, *args, **kwargs) -> None:
        return self._insert_(*args, **kwargs)

    @typing.final
    def update(self, *args, **kwargs) -> None:
        if len(args) == 0 or isinstance(args[0], dict):
            args = [None, *args]
        return self._update_(*args, **kwargs)

    @typing.final
    def remove(self, *args, **kwargs) -> bool:
        return self._remove_(*args, **kwargs)

    @typing.final
    def find(self, *args, **kwargs) -> _T:
        return self._find_(*args, **kwargs)

    @typing.final
    def find_cache(self, path, *args, default_value=_not_found_, **kwargs) -> typing.Any:
        res = Path._do_find(self._cache, path, *args, default_value=_not_found_, **kwargs)
        if res is _not_found_ and self._entry is not None:
            res = self._entry.child(path).find(*args, default_value=_not_found_, **kwargs)
        if res is _not_found_:
            res = default_value
        return res

    @typing.final
    def get_cache(self, path, default_value=_not_found_) -> typing.Any:
        return self.find_cache(path, default_value=default_value)

    @typing.final
    def for_each(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int | str, _T], None, None]:
        yield from self._for_each_(*args, **kwargs)

    # -----------------------------------------------------------------------------
    # 内部接口

    def _insert_(self, value: typing.Any, _op=None, *args, **kwargs):
        return self._update_(None, value, _op or Path.tags.insert, *args, **kwargs)

    def _remove_(self, key: str | int, *args, _deleter: typing.Callable = None, **kwargs) -> bool:
        """删除节点：
        - 将 _cahce 中 path 对应的节点设置为 None，这样访问时不会触发 _entry
        - 若 path 为 None，删除所有子节点
        """
        if callable(_deleter):
            return _deleter(self, key)
        else:
            return self._update_(key, _not_found_, _op=Path.tags.remove, *args, **kwargs)

    def _update_(self, key: str | int, value: typing.Any, _op: Path.tags = None, *args, _setter=None, **kwargs):
        if (key is None or key == []) and value is self:
            pass

        elif isinstance(key, str) and key.startswith("@"):
            value = Path._do_update(self._metadata, key[1:], value, _op, *args, **kwargs)
            if value is not _not_found_:
                return value

        elif callable(_setter):
            _setter(self, key, value)

        else:
            self._cache = Path._do_update(self._cache, key, value, _op, *args, **kwargs)

        return self

    def __missing__(self, key: str | int) -> typing.Any:
        # raise KeyError(f"{self.__class__.__name__}.{key} is not assigned! ")
        return _not_found_

    def _find_(self, key, *args, _getter=None, default_value=_not_found_, **kwargs) -> _T:
        """获取子节点/或属性
        搜索子节点的优先级  cache > getter > entry > default_value
        当 default_value 为 _not_found_ 时，若 cache 中找不到节点，则从 entry 中获得

        """

        if isinstance(key, str) and key.startswith("@"):
            return Path._do_find(self._metadata, key[1:], *args, default_value=_not_found_)

        if isinstance(key, int):
            if key < len(self._cache):
                value = self._cache[key]
            else:
                value = _not_found_
        else:
            value = Path._do_find(self._cache, key, default_value=_not_found_)

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
            self._cache = Path._do_update(self._cache, key, value)
        elif isinstance(key, int) and key <= len(self._cache):
            self._cache.extend([_not_found_] * (key - len(self._cache) + 1))
            self._cache[key] = value
        else:
            self._cache[key] = value

        return value

    def _for_each_(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int | str, _T], None, None]:
        if (self._cache is _not_found_ or len(self._cache) == 0) and self._entry is not None:
            for k, v in self._entry.for_each(*args, **kwargs):
                if not isinstance(v, Entry):
                    yield k, self._type_convert(v, k)
                else:
                    yield k, self._type_convert(_not_found_, k, _entry=v)

        elif self._cache is not None:
            for k, v in Path._do_for_each(self._cache, [], *args, **kwargs):
                _entry = self._entry.child(k) if self._entry is not None else None
                v = self._type_convert(v, k, _entry=_entry)
                yield k, v

    ################################################################################
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

            tp = typing.get_type_hints(get_origin(cls)).get(key, None)

        if tp is None:
            tp = get_args(getattr(self, "__orig_class__", None) or self.__class__)
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
        elif issubclass(get_origin(_type_hint), HTree):
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


def as_htree(*args, **kwargs):
    if len(args) == 0 and len(kwargs) > 0:
        res = Dict(kwargs)
        kwargs = {}
    elif len(args) > 1 and len(kwargs) == 0:
        res = List(list(args))
        args = []
    elif len(args) == 0:
        res = None
    elif isinstance(args[0], HTree):
        res = args[0]
        args = args[1:]
    elif isinstance(args[0], collections.abc.MutableMapping):
        res = Dict(args[0])
        args = args[1:]
    elif isinstance(args[0], collections.abc.MutableSequence):
        res = List(args[0])
        args = args[1:]
    elif len(args) > 1:
        res = List(list(args))
        args = []
    else:
        res = HTree(*args, **kwargs)

    if len(args) + len(kwargs) > 0:
        res._update_(*args, **kwargs)

    return res


class Dict(HTree[_T]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self._cache is _not_found_:
            self._cache = {}

    def children(self) -> typing.Generator[_T, None, None]:
        yield from self.values()

    def __iter__(self) -> typing.Generator[str, None, None]:
        """遍历 children"""
        yield from self.keys()

    def items(self) -> typing.Generator[typing.Tuple[str, _T], None, None]:
        yield from self.for_each()

    def keys(self) -> typing.Generator[str, None, None]:
        for k, v in self.for_each():
            yield k

    def values(self) -> typing.Generator[_T, None, None]:
        for k, v in self.for_each():
            yield v


collections.abc.MutableMapping.register(Dict)


class List(HTree[_T]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self._cache is _not_found_:
            self._cache = []
        elif not isinstance(self._cache, list):
            self._cache = [self._cache]

    def children(self) -> typing.Generator[_T, None, None]:
        for k, v in self.for_each():
            yield v

    def __iter__(self) -> typing.Generator[_T, None, None]:
        for k, v in self.for_each():
            yield v

    def append(self, value):
        return self._insert_(value, Path.tags.append)

    def extend(self, value):
        return self._insert_(value, Path.tags.extend)

    def __iadd__(self, other: list) -> typing.Type[List[_T]]:
        return self.extend(other)


collections.abc.MutableSequence.register(List)
