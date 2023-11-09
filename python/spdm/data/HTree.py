from __future__ import annotations

import collections.abc
import pathlib
import typing
import types
from copy import copy, deepcopy

from ..utils.logger import deprecated, logger
from ..utils.tags import _not_found_, _undefined_
from ..utils.tree_utils import merge_tree_recursive, update_tree
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
    type_convert,
)
from ..utils.uri_utils import URITuple
from .Entry import Entry, open_entry
from .Path import Path, PathLike, Query, as_path


class HTree:
    """
    Hierarchical Tree:

    一种层次化的数据结构，它具有以下特性：
    - 树节点也可以是列表 list，也可以是字典 dict
    - 叶节点可以是标量或数组 array_type，或其他 type_hint 类型
    - 节点可以有缓存（cache)
    - 节点可以有父节点（_parent)
    - 节点可以有元数据（metadata)
        - 包含： 唯一标识（id), 名称（name), 单位（units), 描述（description), 标签（tags), 注释（comment)
    - 任意节点都可以通过路径访问
    - 泛型 _T 变量，为 element 的类型

    @NOTE:
        - Node,Dict,List 不缓存__getitem__结果
        - __getitem__ 返回的类型由 __type_hint__ 决定，默认为 Node
    -
    """

    _metadata = {}

    @classmethod
    def _parser_args(cls, *args, _parent=None, **kwargs):
        if len(args) > 0 and not isinstance(args[0], str):
            _cache = args[0]
            args = args[1:]
        else:
            _cache = None

        _entry = kwargs.pop("_entry", [])

        if not isinstance(_entry, list):
            _entry = [_entry]

        if len(args) > 0:
            _entry.extend(list(args))

        _entry = sum([e if isinstance(e, list) else [e] for e in _entry if e is not None and e is not _not_found_], [])

        _default_value = kwargs.pop("default_value", _not_found_)

        if isinstance(_cache, dict):
            _entry = merge_tree_recursive(_cache.pop("$entry", []), _entry)
            _default_value = update_tree(_default_value, None, _cache.pop("$default_value", _not_found_))

        elif isinstance(_cache, (str, Entry, URITuple, pathlib.Path)):
            _entry = [_cache] + _entry
            _cache = None

        _entry = [v for v in _entry if v is not None and v is not _not_found_]

        kwargs["default_value"] = _default_value

        return _cache, _entry, _parent, kwargs

    def __init__(self, *args, **kwargs) -> None:
        _cache, _entry, _parent, kwargs = HTree._parser_args(*args, **kwargs)

        self._parent = _parent

        self._cache = _cache

        self._entry = open_entry(_entry)

        self._default_value = update_tree({}, None, kwargs.pop("default_value", _not_found_))

        if len(kwargs) > 0:
            self._metadata = merge_tree_recursive(self.__class__._metadata, kwargs)

    def __copy__(self) -> HTree:
        other: HTree = self.__class__.__new__(getattr(self, "__orig_class__", self.__class__))
        other.__copy_from__(self)
        return other

    def __copy_from__(self, other: HTree) -> HTree:
        """复制 other 到 self"""
        if isinstance(other, HTree):
            self._cache = copy(other._cache)
            self._entry = copy(other._entry)
            self._parent = other._parent
            self._default_value = copy(other._default_value)
            if self._metadata is not self.__class__._metadata:
                self._metadata = copy(other._metadata)

        return self

    def __serialize__(self) -> typing.Any:
        return serialize(self.__value__)

    @classmethod
    def __deserialize__(cls, *args, **kwargs) -> HTree:
        return cls(*args, **kwargs)

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} />"

    @property
    def __value__(self) -> typing.Any:
        if self._cache is _not_found_:
            self._cache = merge_tree_recursive(
                self._metadata.get("default_value", None), self._entry.get(default_value=_not_found_)
            )
        return self._cache

    def __array__(self) -> ArrayType:
        return as_array(self.__value__)

    def _repr_svg_(self) -> str:
        from ..view.View import display

        try:
            res = display(self, output="svg")
        except Exception:
            res = ""
        return res

    # def __reduce__(self) -> HTree: raise NotImplementedError(f"")

    def dump(self, entry: Entry = None, **kwargs) -> None:
        """将数据写入 _entry"""
        if entry is None:
            entry = self._entry

        if isinstance(entry, Entry):
            entry.update(self._cache)

    @property
    def __name__(self) -> str:
        return self._metadata.get("name", "unamed")

    @property
    def _root(self) -> HTree | None:
        p = self
        # FIXME: ids_properties is a work around for IMAS dd until we found better solution
        while p._parent is not None and getattr(p, "ids_properties", None) is None:
            p = p._parent
        return p

    def __getitem__(self, path) -> HTree:
        return self.get(path, force=True)

    def __setitem__(self, path, value) -> None:
        self._update(path, value)

    def __delitem__(self, path) -> None:
        return self._remove(path)

    def __contains__(self, key) -> bool:
        return self._query([key], Path.tags.exists)  # type:ignore

    def __len__(self) -> int:
        return self._query([], Path.tags.count)  # type:ignore

    def __iter__(self) -> typing.Generator[HTree, None, None]:
        yield from self.children()

    """ 遍历 children """

    def __equal__(self, other) -> bool:
        return self._query([], Path.tags.equal, other)  # type:ignore

    # def children(self) -> typing.Generator[typing.Any, None, None]: yield from self._foreach()
    # """ 遍历 children """

    def insert(self, *args, **kwargs):
        return self._insert([], *args, **kwargs)

    def update(self, *args, **kwargs):
        return self._update([], *args, **kwargs)

    def remove(self, *args, **kwargs):
        return self._remove(*args, **kwargs)

    def get(self, path: Path | PathLike, default_value: typing.Any = _not_found_, *args, force=False, **kwargs) -> _T:
        path = as_path(path)
        length = len(path)

        if length == 0:
            if force:
                return self
            else:
                return self.__value__

        obj = self

        pos = -1

        for idx, p in enumerate(path[:-1]):
            if p in [Path.tags.ancestors, Path.tags.descendants]:
                pos = idx
                break
            elif isinstance(p, str) and hasattr(obj.__class__, p):
                tmp = getattr(obj, p)
                pos=idx
            elif isinstance(obj, HTree):
                tmp = obj._get(p, default_value=_not_found_, force=True)
                pos = idx

            else:
                tmp = Path(path[idx:]).fetch(obj, default_value=_not_found_)
                pos = len(path)
                break

            if tmp is _not_found_ or pos >= length:
                break
            else:
                obj = tmp

        if path[pos] is Path.tags.ancestors:
            s_pth = path[pos + 1 :]
            while obj is not None and obj is not _not_found_:
                if isinstance(obj, HTree):
                    tmp = obj.get(s_pth, default_value=_not_found_, force=True)
                else:
                    tmp = s_pth.fetch(obj, default_value=_not_found_)
                if tmp is _not_found_:
                    obj = getattr(obj, "_parent", _not_found_)
                else:
                    obj = tmp
                    break
        elif path[pos] is Path.tags.descendants:
            raise NotImplementedError(f"get(descendants) not implemented!")
        elif isinstance(obj, HTree) and pos == length - 2:
            obj = obj._get(path[-1], *args, default_value=default_value, force=force, **kwargs)
        else : 
            # logger.debug(f"Can not find {path} {pos} in {obj}")
            obj = _not_found_

        if obj is _not_found_:
            obj = default_value

        if obj is _undefined_ and pos <= len(path):
            raise KeyError(f"{path[:pos+1]} not found")

        return obj

    def children(self) -> typing.Generator[HTree, None, None]:
        if isinstance(self._cache, list) and len(self._cache) > 0:
            for idx, cache in enumerate(self._cache):
                yield self._as_child(cache, idx, _entry=self._entry.child(idx) if self._entry is not None else None)
        elif isinstance(self._cache, dict) and len(self._cache) > 0:
            for key, cache in self._cache.items():
                yield self._as_child(cache, key, _entry=self._entry.child(key))
        elif self._entry is not None:
            for key, d in self._entry.for_each():
                if not isinstance(d, Entry):
                    yield self._as_child(d, key)
                else:
                    yield self._as_child(None, key, _entry=d)

    ################################################################################
    # Private methods

    def _type_hint(self, path: PathLike = None) -> typing.Type:
        """当 key 为 None 时，获取泛型参数，若非泛型类型，返回 None，
        当 key 为字符串时，获得属性 property 的 type_hint
        """

        path = as_path(path)
        obj = self
        pos = 0
        for idx, p in enumerate(path):
            pos = idx
            if p is Path.tags.parent:
                obj = obj._parent
            elif p is Path.tags.root:
                obj = obj._root
            elif p is Path.tags.current:
                continue
            else:
                break

        path = path[pos:]

        tp_hint = getattr(obj, "__orig_class__", self.__class__)

        for key in path:
            if tp_hint is None:
                break
            elif isinstance(key, str):
                tmp = getattr(getattr(tp_hint, key, None), "type_hint", None)
                if tmp is not None:
                    tp_hint = tmp
                elif typing.get_origin(tp_hint) is None:
                    tp_hints = typing.get_type_hints(tp_hint)
                    tp_hint = tp_hints.get(key, None)
                else:
                    tp_hint = None
            else:
                tmp = get_args(tp_hint)
                if len(tmp) == 0:
                    tp_hint = None
                else:
                    tp_hint = tmp[-1]

        # logger.debug((path, tp_hint))

        return tp_hint

    def _as_child(
        self,
        value,
        key,
        *args,
        default_value=_not_found_,
        _type_hint: typing.Type = None,
        _entry: Entry | None = None,
        _parent: HTree | None = None,
        _getter: typing.Callable | None = None,
        force=False,
        **kwargs,
    ) -> _T:
        if force and value is _not_found_ and (_entry is None or not _entry.exists):
            return _not_found_

        if isinstance(key, str) and isinstance(self._default_value, dict):
            s_default_value = deepcopy(self._default_value.get(key, _not_found_))

        else:
            s_default_value = deepcopy(self._default_value)

        default_value = merge_tree_recursive(s_default_value, default_value)

        if _parent is None:
            _parent = self

        if _type_hint is None:
            _type_hint = self._type_hint(key if key is not None else 0)

        force = _type_hint is None and default_value is _undefined_

        if isinstance(_type_hint, typing.types.UnionType):
            tp = typing.get_args(_type_hint)
            if len(tp) > 2 or tp[1] is not type(None):
                logger.debug(f"ignore {tp[1:]}")

            _type_hint = tp[0]

            if value is _not_found_ or value is None:
                if not isinstance(_entry, Entry):
                    pass
                elif _entry.is_leaf:
                    value = _entry.get()
                    _entry = None
                elif _entry.is_list:
                    _type_hint = List[_type_hint]
                elif not _entry.exists:
                    value = _not_found_
                    _entry = None
            elif isinstance(value, (bool, int, float, str, array_type)):
                _entry = None

            if isinstance(value, HTree):
                pass
            elif (isinstance(value, (dict, list)) or _entry is not None) and issubclass(get_origin(_type_hint), HTree):
                value = _type_hint(value, _entry=_entry, _parent=_parent, **kwargs)
        else:
            if not issubclass(get_origin(_type_hint), HTree) and value is _not_found_ and _entry is not None:
                value = _entry.get(default_value=_not_found_)
                _entry = None

            if (
                not isinstance_generic(value, _type_hint)
                and _getter is not None
                and (_entry is None or not _entry.exists)
            ):
                try:
                    tmp = _getter(self)
                except Exception as error:
                    raise RuntimeError(f"{self.__class__} id={key}: 'getter' failed!") from error
                else:
                    value = tmp
                    _entry = None

            if isinstance_generic(value, _type_hint):
                pass

            elif not force and issubclass(get_origin(_type_hint), HTree):
                value = _type_hint(value, _entry=_entry, _parent=_parent, default_value=default_value, **kwargs)

            elif not force and isinstance(value, HTree):
                value = value.__value__

            elif not force and isinstance(value, Entry):
                value = value.__value__

            else:
                if value is _not_found_:
                    value = default_value

                if _type_hint is array_type:
                    if isinstance(value, (list)) or isinstance(value, array_type):
                        pass

                if _type_hint is not None:
                    value = type_convert(
                        value, _type_hint=_type_hint, _parent=_parent, default_value=default_value, **kwargs
                    )

        return value

    def _get(self, query: PathLike = None, *args, _type_hint=None, **kwargs) -> HTree:
        """获取子节点"""

        value = _not_found_

        if query is None:  # get value from self._entry and update cache
            return self

        elif query is Path.tags.current:
            value = self

        elif query is Path.tags.parent:
            value = self._parent
            # if hasattr(value, "_identifier"):
            #     value = value._identifier

        elif query is Path.tags.next:
            raise NotImplementedError(f"TODO: operator 'next'!")
            # value = self._parent.next(self)

        elif query is Path.tags.root:
            value = self._root

        elif isinstance(query, (int, slice, tuple, Query)):
            if _type_hint in numeric_type:
                value = self._get_as_array(query, *args, _type_hint=_type_hint, **kwargs)
            else:
                value = self._get_as_list(query, *args, _type_hint=_type_hint, **kwargs)

        elif isinstance(query, str):
            value = self._get_as_dict(query, *args, _type_hint=_type_hint, **kwargs)

        elif isinstance(query, set):  # compound
            raise NotImplementedError(f"TODO: NamedDict")
            # value = NamedDict(cache={k: self._get_as_dict(
            #     k, type_hint=type_hint, *args,  **kwargs) for k in query})

        else:
            raise NotImplementedError(f"TODO: {(query)}")

        return value  # type:ignore

    def _get_as_array(self, idx, *args, default_value=_not_found_, **kwargs) -> NumericType:
        if self._cache is _not_found_:
            self._cache = self._entry.__value__  # type:ignore

        if isinstance(self._cache, array_type) or isinstance(self._cache, collections.abc.Sequence):
            return self._cache[idx]

        elif self._cache is _not_found_:
            return default_value  # type:ignore

        else:
            raise RuntimeError(f"{self._cache}")

    def _get_as_dict(self, key: str, *args, default_value=_not_found_, **kwargs) -> HTree:
        cache = _not_found_

        if isinstance(self._cache, collections.abc.Mapping):
            cache = self._cache.get(key, _not_found_)

        _type_hint = kwargs.pop("_type_hint", None) or self._type_hint(key)

        if isinstance_generic(cache, _type_hint):
            value = cache
        else:
            if self._entry is not None:
                _entry = self._entry.child(key)
            else:
                _entry = None

            value = self._as_child(
                cache, key, *args, _entry=_entry, _type_hint=_type_hint, default_value=default_value, **kwargs
            )

            if self._cache is _not_found_ or self._cache is None:
                self._cache = {}

            self._cache[key] = value

        return value

    def _get_as_list(self, key: PathLike, *args, default_value=_not_found_, _parent=None, **kwargs) -> HTree:
        if isinstance(key, (Query, dict)):
            raise NotImplementedError(f"TODO: {key}")
            # cache = QueryResult(self, key, *args, **kwargs)
            # _entry = None
            # key = None

        elif isinstance(key, int):
            if isinstance(self._cache, list) and key < len(self._cache):
                cache = self._cache[key]
                if isinstance(key, int) and key < 0:
                    key = len(self._cache) + key
            else:
                cache = _not_found_

            if isinstance(self._entry, Entry):
                _entry = self._entry.child(key)
            else:
                _entry = self._entry

        elif isinstance(key, slice):
            start = key.start or 0
            stop = key.stop
            step = key.step or 1

            if isinstance(self._cache, list):
                if stop is not None and stop < 0 and start >= len(self._cache):
                    raise NotImplementedError()
                else:
                    cache = self._cache[slice(start, stop, step)]
            else:
                cache = _not_found_

            _entry = self._entry.child(key)

        elif self._cache is _not_found_ or self._cache is None:
            _entry = self._entry.child(key)
            cache = None

        else:
            raise RuntimeError((key, self._cache, self._entry))

        default_value = merge_tree_recursive(self._metadata.get("default_value", _not_found_), default_value)

        value = self._as_child(
            cache, key, *args, _entry=_entry, _parent=_parent or self._parent, default_value=default_value, **kwargs
        )

        if isinstance(key, int):
            if self._cache is _not_found_:
                self._cache = []
            elif not isinstance(self._cache, list):
                raise ValueError(self._cache)

            if key >= len(self._cache):
                self._cache.extend([_not_found_] * (key - len(self._cache) + 1))

        if isinstance(key, int) and (key < 0 or key >= len(self._cache)):
            raise IndexError(f"Out of range  {key} > {len(self._cache)}")

        if isinstance(key, int) and key >= 0:
            self._cache[key] = value

        return value

    def _query(self, path: PathLike, *args, default_value=_not_found_, **kwargs) -> HTree:
        res = as_path(path).fetch(self._cache, *args, default_value=_not_found_, **kwargs)
        if res is _not_found_:
            res = self._entry.child(path).fetch(*args, default_value=default_value, **kwargs)
        return res

    def _insert(self, path: PathLike, *args, **kwargs):
        self._cache = as_path(path).insert(self._cache, *args, **kwargs)
        return self

    def _update(self, path: PathLike, *args, **kwargs):
        self._cache = as_path(path).update(self._cache, *args, **kwargs)
        return self

    def _remove(self, path: PathLike, *args, **kwargs) -> None:
        self.update(path, _not_found_)
        self._entry.child(path).remove(*args, **kwargs)

    @deprecated
    def _find_next(
        self, query: PathLike, start: int | None, default_value=_not_found_, **kwargs
    ) -> typing.Tuple[typing.Any, int | None]:
        if query is None:
            query = slice(None)

        cache = None
        _entry = None
        next_id = start
        if isinstance(query, slice):
            start_q = query.start or 0
            stop = query.stop
            step = query.step
            if start is None:
                start = start_q
            else:
                start = int((start - start_q) / step) * step

            next_id = start + step
            if isinstance(self._cache, list) and start < len(self._cache):
                cache = self._cache[start]
            _entry = self._entry.child(start)

        elif isinstance(query, Query):
            pass

        if start is not None:
            return self._as_child(cache, start, _entry=_entry, default_value=default_value, **kwargs), next_id
        else:
            return None, None


def as_htree(obj, *args, **kwargs):
    if isinstance(obj, HTree):
        return obj
    else:
        return HTree(obj, *args, **kwargs)


Node = HTree

_T = typing.TypeVar("_T")


class Container(HTree, typing.Generic[_T]):
    """
    带有type hint的容器，其成员类型为 _T，用于存储一组数据或对象，如列表，字典等
    """

    pass


class Dict(Container[_T]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for cls in [*self.__class__.__bases__, self.__class__]:
            # TODO: 需要优化，去掉重复操作
            metadata = getattr(cls, "_metadata", _not_found_)
            self._cache = update_tree(self._cache, None, deepcopy(metadata), _idempotent=True)

    def __iter__(self) -> typing.Generator[str, None, None]:
        """遍历 children"""
        for k in self.children():
            yield k

    def items(self):
        yield from self.children()

    def __contains__(self, key: str) -> bool:
        return (isinstance(self._cache, collections.abc.Mapping) and key in self._cache) or self._entry.child(
            key
        ).exists

    def __getitem__(self, path) -> _T:
        tp_hint = get_args(self)[-1]
        return super().get(path, _type_hint=tp_hint, force=True)


class List(Container[_T]):
    def __init__(self, cache: typing.Any = None, *args, **kwargs) -> None:
        if cache is _not_found_ or cache is None:
            cache = []
        elif not isinstance(cache, collections.abc.Sequence):
            cache = [cache]
        super().__init__(cache, *args, **kwargs)

    @property
    def empty(self) -> bool:
        return self._cache is None or self._cache is _not_found_ or len(self._cache) == 0

    def __len__(self) -> int:
        if self._cache is not None and len(self._cache) > 0:
            return len(self._cache)
        elif self._entry is not None:
            return self._entry.fetch(Path.tags.count)
        return 0

    def __iter__(self) -> typing.Generator[_T, None, None]:
        """遍历 children"""
        for v in self.children():
            if isinstance(v, HTree):
                v._parent = self._parent
            yield v

    def __getitem__(self, path) -> _T:
        return super().get(path, _parent=self._parent, force=True)

    def dump(self, _entry: Entry, **kwargs) -> None:
        """将数据写入 _entry"""
        _entry.insert([{}] * len(self._cache))
        for idx, value in enumerate(self._cache):
            if isinstance(value, HTree):
                value.dump(_entry.child(idx), **kwargs)
            else:
                _entry.child(idx).insert(value)
