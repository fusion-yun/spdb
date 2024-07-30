""" Hierarchical Tree (HTree) is a hierarchical data structure that can be used to
 store a group of data or objects, such as lists, dictionaries, etc.  """

import collections.abc
import typing
import inspect
from copy import deepcopy, copy
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, as_array, primary_type, PrimaryType, type_convert

from spdm.core.entry import Entry, as_entry
from spdm.core.query import Query
from spdm.core.path import Path, PathLike, as_path
from spdm.core.generic import Generic


class HTreeNode:
    """Hierarchical Tree Structured Data: HTreeNode is a node in the hierarchical tree."""

    def __init__(
        self, cache=_not_found_, /, _entry: Entry = None, _parent: typing.Self = None
    ):  # pylint: disable=C0103
        """Initialize a HTreeNode object."""

        self._cache = cache
        self._entry = as_entry(_entry)
        self._parent: HTreeNode = _parent
        super().__init__()

    def __copy__(self) -> typing.Self:
        other = object.__new__(self.__class__)
        other._cache = deepcopy(self._cache)
        other._entry = copy(self._entry)
        return other

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

    @classmethod
    def _getstate(cls, obj: typing.Any) -> dict:
        if isinstance(obj, dict):
            return {k: cls._getstate(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._getstate(v) for v in obj]
        elif hasattr(obj.__class__, "__getstate__"):
            return obj.__getstate__()
        else:
            return obj

    @classmethod
    def _setstate(cls, target, state: dict):
        if isinstance(state, HTree):
            target = cls._setstate(target, state._cache)
        elif state is _not_found_:
            pass
        elif target is _not_found_:
            target = state
        elif isinstance(target, dict) and isinstance(state, dict):
            for k, v in state.items():
                target[k] = cls._setstate(target.get(k, _not_found_), v)
        elif hasattr(target.__class__, "__setstate__"):
            target.__setstate__(state)
        else:
            target = state

        return target

    def __getstate__(self) -> dict:
        state: dict = self._getstate(self._cache)
        if not isinstance(state, dict):
            state = {"$value": state}

        state.update(
            {
                "$type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                # "$path": ".".join(self.__path__),
                # "$name": self.__name__,
                "$entry": self._entry.__getstate__(),
            }
        )

        return state

    def __delstate__(self, *args, **kwargs) -> None:
        # self._entry = None
        self._cache = _not_found_

    def __setstate__(self, *args, **kwargs) -> None:
        self._entry = None
        self._cache = _not_found_
        for state in [*args, kwargs]:
            if isinstance(state, dict):
                self._entry = as_entry(
                    [
                        state.pop("_entry", _not_found_),
                        state.pop("$entry", _not_found_),
                       self._entry ,
                    ]
                )

            self._cache = self._setstate(self._cache, state)

    def duplicate(self) -> typing.Self:
        return self.__class__(self.__getstate__(), _entry=self._entry, _parent=self._parent)

    @typing.final
    def clear(self):
        return self.__delstate__()

    @property
    def __label__(self) -> str:
        # return self.__class__.__name__
        return Path("_metadata/label").get(self, ".".join(self.__path__))

    # @property
    # def __name__(self) -> str:
    #     return self._metadata.get("name", self.__class__.__name__)
    # @property
    # def __path__(self) -> typing.List[str | int]:
    #     if isinstance(self._parent, HTreeNode):
    #         return self._parent.__path__ + [self.__name__]
    #     else:
    #         return [self.__name__]
    # def __str__(self) -> str:
    #     return f"<{self.__class__.__name__} name='{'.'.join(self.__path__)}' />"
    # def __repr__(self) -> str:
    #     return ".".join(self.__path__)
    # @property
    # def __root__(self) -> typing.Self | None:
    #     p = self
    #     while isinstance(p, HTreeNode) and p._parent is not None:
    #         p = p._parent
    #     return p

    def query(self, *args, **kwargs) -> typing.Any:
        """查询（Query）节点的值。"""
        return Path(*args).query(self, **kwargs)

    @typing.final
    def read(self, *args, **kwargs) -> typing.Any:
        """读取（Read）访问节点的值。"""
        res = self.query(*args, **kwargs)
        return res.__value__ if isinstance(res, HTreeNode) else res

    def update(self, *args, **kwargs):
        self._cache = Path(*args[:-1]).update(self._cache, *args[-1:], **kwargs)

    def fetch(self):
        """fetch data from  entry to cache"""
        if self._entry is not None:
            self._cache = Path().update(self._cache, self._entry.dump)
        return self

    def flush(self) -> None:
        """flush data from cache to entry"""
        if self._entry is not None:
            self._entry.update(self._cache)

    @typing.final
    def parent(self) -> typing.Self:
        """父节点"""
        return self if not isinstance(self._parent, HTreeNode) else self._parent.parent

    @typing.final
    def ancestors(self) -> typing.Generator[typing.Self, None, None]:
        """遍历祖辈节点"""
        obj = self._parent
        while obj is not None:
            yield obj
            obj = getattr(obj, "_parent", None)

    def children(self) -> typing.Generator[typing.Self, None, None]:
        """遍历子节点 (for HTree)"""

    @typing.final
    def descendants(self, traversal_strategy="deep_first") -> typing.Generator[typing.Self, None, None]:
        """遍历所有子孙辈节点"""

        match traversal_strategy:
            case "breadth-first":
                tmp: typing.List[HTree] = []
                for child in self.children():
                    if isinstance(child, HTree):
                        tmp.append(child)
                    yield child
                for child in tmp:
                    yield from child.descendants(traversal_strategy=traversal_strategy)

            case "deep_first":
                for child in self.children():
                    yield child
                    if isinstance(child, HTree):
                        yield from child.descendants(traversal_strategy=traversal_strategy)

            case _:
                raise NotImplementedError(f"Traversal strategy '{traversal_strategy}' is not implemented!")

    @typing.final
    def siblings(self):
        if isinstance(self._parent, HTree):
            yield from filter(lambda x: x is not self, self._parent.children())

    ############################################################################################
    # Python special methods

    @property
    def __value__(self) -> PrimaryType:
        if self._cache is _not_found_ and self._entry is not None:
            self._cache = self._entry.get()
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

    # def __bool__(self) -> bool:
    #     return self.query(Query.tags.equal, True)

    def __equal__(self, other) -> bool:
        """比较节点的值是否相等"""
        return self.query(Query.tags.equal, other if not isinstance(other, HTreeNode) else other.__value__)


_T = typing.TypeVar("_T")


class HTree(HTreeNode):
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

    ## Path：
      - path 指向
    """

    def __init__(self, cache: typing.Any = ..., /, _entry: Entry = None, _parent: HTreeNode = None, **kwargs):
        """Initialize a HTree object."""
        if not (isinstance(cache, (dict, list)) or cache is _not_found_):
            raise TypeError(
                f"Invalid cache type, cache must be a dict or _not_found_ not {type(cache)} {self.__class__}!"
            )
        if len(kwargs) > 0:
            cache = Path().update(cache, kwargs)
        super().__init__(cache, _entry=_entry, _parent=_parent)

    @property
    def is_leaf(self) -> bool:
        """只读属性，返回节点是否为叶节点"""
        return False

    # -----------------------------------------------------------------------------------------------------------
    # CRUD API

    def update(self, *args, **kwargs) -> None:
        """Update 更新元素的value、属性，或者子元素的树状结构"""
        Path(*args[:-1]).update(self, *args[-1:], **kwargs)

    def insert(self, *args, **kwargs) -> None:
        """插入（Insert） 在树中插入一个子节点。插入操作是非幂等操作"""
        Path(*args[:-1]).insert(self, *args[-1:], **kwargs)

    def delete(self, *args, **kwargs) -> None:
        """删除（delete）节点。"""
        Path(*args).delete(self, **kwargs)

    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """搜索（Search ）符合条件节点或属性。查询是一个幂等操作，它不会改变树的状态。
        - 返回一个迭代器，允许用户在遍历过程中处理每个节点。
        """
        yield from Path(*args[:1]).search(self, *args[1:], **kwargs)

    def find(self, *args, **kwargs):
        """查找（Find)，返回第一个 search 结果"""
        return Path(*args[:1]).find(self, *args[1:], **kwargs)

    def query(self, *args, **kwargs):
        """查询（Query）， args[-1] 为 projection"""
        return Path(*args[:1]).query(self, *args[1:], **kwargs)

    # -----------------------------------------------------------------------------------
    # alias

    def put(self, *args, **kwargs) -> None:
        """Put, alias of update"""
        return self.update(*args, **kwargs)

    def get(self, path, default_value: typing.Any = _not_found_) -> typing.Any:
        """Get , alias of query"""
        return self.find(path, default_value=default_value)

    def pop(self, path, default_value: typing.Any = _not_found_) -> typing.Any:
        """Pop , query and delete"""
        node = self.find(path, default_value=_not_found_)
        if node is not _not_found_:
            self.delete(path)
            return node
        else:
            return default_value

    # -----------------------------------------------------------------------------------
    # Python special methods

    def __getitem__(self, key: PathLike) -> typing.Any:
        """Get item from tree by path. 当找不到时，调用 __missing__ 方法"""
        value = self.find(key, default_value=_not_found_)
        return value if value is not _not_found_ else self.__missing__(key)

    def __setitem__(self, key: PathLike, value) -> None:
        """Set item to tree by path. alias of update"""
        return self.update(key, value)

    def __delitem__(self, key: PathLike) -> None:
        """Delete item. alias of delete"""
        return self.delete(key)

    def __missing__(self, key: PathLike) -> typing.Any:
        """fallback 当 __getitem__ 没有找到元素时被调用"""
        raise KeyError(key)
        # return _not_found_

    def __contains__(self, key: PathLike) -> bool:
        """检查 path 是否存在"""
        return self.query(key, Query.tags.exists)

    def __equal__(self, other) -> bool:
        return self.query({Query.tags.equal: other})

    def __iter__(self) -> typing.Generator[HTreeNode, None, None]:
        """遍历子节点"""
        yield from self.children()

    def children(self) -> typing.Generator[HTreeNode, None, None]:
        """遍历子节点 (for HTree)"""
        yield from self.search(["*"])

    def __len__(self) -> int:
        """返回子节点的数量"""
        return self.__find__(Query.tags.count)

    # -----------------------------------------------------------------------------
    # API as container

    def __as_node__(
        self,
        key,
        value,
        type_hint=None,
        entry=None,
        parent=None,
        default_value=_not_found_,
        metadata=None,
    ) -> typing.Self:

        if parent is None:
            parent = self

        if type_hint is _not_found_:
            type_hint = None

        if type_hint is None and isinstance(key, str) and key.isidentifier():
            orig_cls = typing.get_origin(self.__class__) or self.__class__
            type_hint = typing.get_type_hints(orig_cls).get(key, None)

        if type_hint is None:
            type_hint = getattr(self.__class__, "__args__", None)

        if isinstance(type_hint, tuple):
            type_hint = type_hint[-1]

        orig_tp = typing.get_origin(type_hint) or type_hint

        if inspect.isclass(orig_tp) and issubclass(orig_tp, HTreeNode):
            if (value is _not_found_) and (entry is None or not entry.exists):
                entry = None
                if isinstance(default_value, dict):
                    value = Path().update(copy(default_value), value)
                else:
                    value = default_value
                default_value = _not_found_

            if value is _not_found_ and entry is None:
                node = value
            elif isinstance(value, orig_tp):
                node = value
            else:
                node = type_hint(value, _entry=entry, _parent=parent)

        else:
            if value is _not_found_ and entry is not None:
                value = entry.get()

            if value is _not_found_:
                value = default_value

            elif isinstance(default_value, dict):
                value = Path().update(copy(default_value), value)
                default_value = _not_found_

            if value is _not_found_:
                node = value
            else:
                node = type_convert(type_hint, value)

        if isinstance(node, HTreeNode):
            if node._parent is None:
                node._parent = self
        if isinstance(node, HTree) and metadata is not None and len(metadata) > 0:
            node._metadata = Path().update(deepcopy(getattr(node, "_metadata", {})), metadata)

        if node is not _not_found_ and key is not None:
            self._cache = Path([key]).update(self._cache, node)

        return node

    def __get_node__(
        self,
        key,
        /,
        getter=None,
        type_hint=None,
        entry=None,
        parent=None,
        default_value=_not_found_,
        metadata=None,
    ) -> HTreeNode:
        if key is None:
            return self

        value = Path([key]).get(self._cache, _not_found_)

        if value is _not_found_ and callable(getter):
            value = getter(self)

        if entry is None and self._entry is not None:
            entry = self._entry.child(key)

        return self.__as_node__(
            key,
            value,
            type_hint=type_hint,
            entry=entry,
            parent=parent,
            default_value=default_value,
            metadata=metadata,
        )

    def __set_node__(self, key, *args, setter=None, **kwargs) -> None:
        if callable(setter):
            setter(self, key, *args, **kwargs)
        else:
            self._cache = Path([key] if key is not None else []).update(self._cache, *args, **kwargs)

        return self

    def __del_node__(self, key: str | int, deleter=None) -> bool:
        if callable(deleter):
            return deleter(self, key)
        elif (isinstance(self._cache, collections.abc.MutableMapping) and key in self._cache) or (
            isinstance(self._cache, collections.abc.Sequence) and key < len(self._cache)
        ):
            self._cache[key] = _not_found_
            return True
        else:
            return False

    def __find__(self, predicate, *args, **kwargs) -> typing.Any:
        res = Path().find(self._cache, predicate, *args, **kwargs)
        if res is _not_found_ and self._entry is not None:
            res = self._entry.find(predicate, args, **kwargs)
        return res

    def __search__(self, *args, **kwargs) -> typing.Generator[HTreeNode, None, None]:

        cached_key = []
        for key, value in Path().search(self._cache, Query.tags.get_item):
            if isinstance(key, (str, int)):
                cached_key.append(key)
                entry = None if self._entry is None else self._entry.child(key)
                node = self.__as_node__(key, value, entry=entry)
                yield Path().find(node, *args, **kwargs)
            else:
                yield Path().find(value, *args, **kwargs)

        if self._entry is not None:
            for key, entry in self._entry.search(Query.tags.get_item):
                if not isinstance(key, (str, int)) or key in cached_key:
                    continue
                node = self.__as_node__(key, _not_found_, entry=entry)
                yield Path().find(node, *args, **kwargs)


class Dict(Generic[_T], HTree):
    """Dict 类型的 HTree 对象"""

    def __init__(self, cache: dict = _not_found_, /, **kwargs):
        if cache is _not_found_:
            cache = {}
        elif isinstance(cache, dict):
            pass
        elif isinstance(cache, collections.abc.Iterable):
            cache = dict(cache)
        else:
            raise TypeError(f"Invalid args {cache}")

        cache = Path().update(cache, {k: kwargs.pop(k) for k in list(kwargs.keys()) if not k.startswith("_")})

        super().__init__(cache, **kwargs)

    def keys(self) -> typing.Generator[str, None, None]:
        """遍历 key"""
        if isinstance(self._cache, collections.abc.Mapping):
            yield from self._cache.keys()

        if self._entry is not None:
            for key in self._entry.keys():
                if key not in self._cache:
                    yield key

    @typing.final
    def items(self) -> typing.Generator[typing.Tuple[str, _T], None, None]:
        """遍历 key,value"""
        for key in self.keys():
            yield key, self.__get_node__(key)

    @typing.final
    def values(self) -> typing.Generator[_T, None, None]:
        """遍历 value"""
        for key in self.keys():
            yield self.__get_node__(key)

    def children(self) -> typing.Generator[_T, None, None]:
        """遍历子节点"""
        for k in self.keys():
            yield self.__get_node__(k)

    @typing.final
    def __iter__(self) -> typing.Generator[str, None, None]:
        """遍历，sequence 返回子节点的值，mapping 返回子节点的键"""
        yield from self.keys()

    def __len__(self) -> int:
        """返回子节点的数量"""
        if self._entry is not None:
            return len([*self.keys()])
        elif self._cache is not _not_found_:
            return len(self._cache)
        else:
            return 0


collections.abc.MutableMapping.register(Dict)


class List(Generic[_T], HTree):
    """List 类型的 HTree 对象"""

    def __init__(self, cache: list = _not_found_, **kwargs):
        if cache is _not_found_:
            cache = []
        elif isinstance(cache, list):
            pass
        elif isinstance(cache, collections.abc.Iterable):
            cache = list(cache)
        else:
            raise TypeError(f"Invalid args {cache}")

        super().__init__(cache, **kwargs)

    @property
    def is_sequence(self) -> bool:
        """只读属性，返回节点是否为 Sequence"""
        return True

    def append(self, value):
        """append value to list"""
        return self.insert(value)

    def extend(self, value):
        """extend value to list"""
        return self.update(Path.tags.extend, value)

    def __iadd__(self, other: list) -> typing.Self:
        return self.extend(other)

    def __contains__(self, path_or_node: PathLike | Path | HTreeNode) -> bool:
        """查找，sequence 搜索值，mapping搜索键"""
        if isinstance(path_or_node, PathLike):
            return super().__contains__(path_or_node)
        return self.query(path_or_node, Query.tags.exists)

    def __len__(self) -> int:
        """返回子节点的数量"""
        length = 0

        if isinstance(self._cache, collections.abc.Sequence):
            length = len(self._cache)

        if self._entry is not None:
            length = max(length, self._entry.count)

        return length

    def children(self) -> typing.Generator[_T, None, None]:
        """遍历子节点"""
        for idx in range(len(self)):
            yield self.__get_node__(idx)

    def __iter__(self) -> typing.Generator[_T, None, None]:
        """遍历，sequence 返回子节点的值，mapping 返回子节点的键"""
        yield from self.search()

    def __getitem__(self, key) -> _T:
        return super().__getitem__(key)

    # def __missing__(self, idx: int) -> typing.Any:
    #     """fallback 当 __getitem__ 没有找到元素时被调用"""
    #     if not isinstance(idx, int):
    #         return super().__missing__(idx)
    #     if self._cache is _not_found_:
    #         self._cache = [_not_found_] * (idx + 1)
    #     else:
    #         self._cache.extend([_not_found_] * (idx + 1 - len(self._cache)))

    #     return self._cache[idx]


collections.abc.MutableSequence.register(List)


class Set(Generic[_T], HTree):
    """hashable 对象的容器"""

    def __init__(self, cache: dict = _not_found_, /, **kwargs):
        super().__init__({}, **kwargs)
        if isinstance(cache, list):
            for v in cache:
                self.insert(v)
        elif cache is _not_found_ and self._entry is not None:
            for item in self._entry.search(Query.tags.get_value):
                if isinstance(item, Entry):
                    node = self.__as_node__(None, _not_found_, entry=item, parent=self)
                else:
                    node = self.__as_node__(None, item, parent=self)

                self._cache[hash(node)] = node

        elif cache is not _not_found_:
            raise TypeError(f"Invalid args {cache}")
        return

    def find(self, key, *args, **kwargs) -> _T:
        if not isinstance(key, int):
            return super().find(hash(key), *args, **kwargs)
        else:
            return super().find(key, *args, **kwargs)

    def update(self, key, *args, **kwargs) -> None:
        if isinstance(key, str):
            kwargs["metadata"] = {"label": key}
        super().__as_node__(hash(key), *args, **kwargs)

    def insert(self, value, *args, **kwargs) -> None:
        node = super().__as_node__(None, value, *args, **kwargs)
        self._cache = Path([hash(node)]).update(self._cache, node, *args, **kwargs)

    def delete(self, key, *args, **kwargs) -> None:
        return super().delete(hash(key), *args, **kwargs)

    def __getitem__(self, key) -> _T:
        return super().__getitem__(key)

    def __iter__(self) -> typing.Generator[_T, None, None]:
        yield from self._cache.values()

    def __search__(self, *args, **kwargs) -> typing.Generator[_T, None, None]:
        for value in self.__iter__():
            yield Path().find(value, *args, **kwargs)


collections.abc.Set.register(Set)
