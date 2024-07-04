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
from spdm.core.path import Path, Query, PathLike, as_path
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
    """Hierarchical Tree Structured Data: HTreeNode is a node in the hierarchical tree."""

    def __init__(
        self,
        cache=_not_found_,
        /,
        _entry: Entry = None,
        _parent: typing.Self = None,
        _metadata=_not_found_,
        **kwargs,
    ):
        """Initialize a HTreeNode object."""
        self._cache = cache
        self._entry = as_entry(_entry) if _entry is not None else None
        self._parent = _parent
        self._metadata = deepcopy(getattr(self.__class__, "_metadata", _not_found_))
        self._metadata = Path().update(self._metadata, _metadata)
        self._metadata = Path().update(self._metadata, kwargs)
        super().__init__()

    def __copy__(self) -> typing.Self:
        other = object.__new__(self.__class__)
        other._cache = deepcopy(self._cache)
        other._entry = copy(self._entry)
        other._metadata = deepcopy(self._metadata)
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

    def __getstate__(self) -> dict:
        state: dict = super().__getstate__()
        state.update(
            {
                "$type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                "$path": ".".join(self.__path__),
                "$name": self.__name__,
                "$entry": self._entry.__getstate__(),
                "$metadata": self._metadata,
            }
        )

        if isinstance(self._cache, collections.abc.Mapping):
            state.update(get_state(self._cache))
        else:
            state["$data"] = get_state(self._cache)

        return state

    def __setstate__(self, state: dict) -> dict | None:

        self._entry = as_entry(state.pop("$entry", None))
        self._metadata = state.pop("$metadata", {})

        logger.verbose(f"Load {self.__class__.__name__} from state: {state.pop('$type',None)}")

        self._cache = state.pop("$data", _not_found_)

        if self._cache is _not_found_:
            self._cache = state
            state = {}
        # elif len(state) > 0:
        #     logger.warning(f"Ignore property {list(state.keys())}")

        return super().__setstate__(state)

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
    def __root__(self) -> typing.Self | None:
        p = self
        while isinstance(p, HTreeNode) and p._parent is not None:
            p = p._parent
        return p

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

    def flush(self):
        """flush data from cache to entry"""
        if self._entry is not None:
            self._entry.update(self._cache)
        return self

    @typing.final
    def parent(self) -> typing.Self:
        """父节点"""
        return self._parent

    @typing.final
    def ancestors(self) -> typing.Generator[typing.Self, None, None]:
        """遍历祖辈节点"""
        obj = self._parent
        while obj is not None:
            yield obj
            obj = getattr(obj, "_parent", None)

    def children(self) -> typing.Generator[typing.Self | PrimaryType, None, None]:
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
        return as_array(self.read())

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


_T = typing.TypeVar("_T")
_TR = typing.TypeVar("_TR")  # return value type


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

    @property
    def is_leaf(self) -> bool:
        """只读属性，返回节点是否为叶节点"""
        return False

    # -----------------------------------------------------------------------------------------------------------
    # CRUD API
    @typing.final
    def update(self, *args, **kwargs) -> None:
        """Update 更新元素的value、属性，或者子元素的树状结构"""
        return Path(*args[:-1]).update(self, *args[-1:], **kwargs)

    @typing.final
    def insert(self, *args, **kwargs):
        """插入（Insert） 在树中插入一个子节点。插入操作是非幂等操作"""
        return Path(*args[:-1]).insert(self, *args[-1:], **kwargs)

    @typing.final
    def create(self, *args, **kwargs):
        """创建（Create） 通常指的是创建一个新的子节点。由于是在树上创建，与“插入” 同义，alias of insert"""
        return self.insert(*args, **kwargs)

    @typing.final
    def delete(self, *args, **kwargs) -> bool:
        """删除（delete）节点。"""
        return Path(*args).delete(self, **kwargs)

    @typing.final
    def put(self, *path_and_value):
        """Put, alias of update"""
        return self.update(*path_and_value)

    @typing.final
    def get(self, key=None, default_value=_not_found_) -> _T:
        """Get , alias of query"""
        return self.find(key, default_value=default_value)

    @typing.final
    def pop(self, path, default_value=_not_found_) -> typing.Any:
        """Pop , query and delete"""
        node = self.find(path, default_value=_not_found_)

        if node is not _not_found_:
            self.delete(path)
            return node

        return default_value

    @typing.final
    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """搜索（Search ）符合条件节点或属性。查询是一个幂等操作，它不会改变树的状态。
        - 返回一个迭代器，允许用户在遍历过程中处理每个节点。
        """
        yield from Path(*args).search(self, **kwargs)

    @typing.final
    def traversal(self, *args, **kwargs) -> typing.Generator[_T, None, None]:
        """遍历（Traversal），遍历树中的子节点 。 alias of search"""
        yield from self.search(*args, **kwargs)

    @typing.final
    def find(self, *args, **kwargs) -> _T:
        """查找（Find)，返回第一个 search 结果"""
        return Path(*args[:1]).find(self, *args[1:], **kwargs)

    @typing.final
    def query(self, *args, **kwargs) -> _TR:
        """查询（Query）， args[-1] 为 projection"""
        return Path(*args[:1]).query(self, *args[1:], **kwargs)

    # -----------------------------------------------------------------------------------
    # Python special methods

    @typing.final
    def __getitem__(self, *path: PathLike) -> _T:
        """Get item from tree by path. 当找不到时，调用 __missing__ 方法"""
        node = self.get(Path(*path), default_value=_not_found_)
        return node if node is not _not_found_ else self.__missing__(path)

    @typing.final
    def __setitem__(self, path: PathLike, value) -> None:
        """Set item to tree by path. alias of update"""
        if isinstance(path, tuple):
            return self.update(*path, value)
        else:
            return self.update(path, value)

    @typing.final
    def __delitem__(self, *path: PathLike) -> None:
        """Delete item. alias of delete"""
        return self.delete(*path)

    def __missing__(self, path: PathLike) -> typing.Any:
        """fallback 当 __getitem__ 没有找到元素时被调用"""
        # raise KeyError(f"{self.__class__.__name__}.{key} is not assigned! ")
        logger.verbose(f"{self.__class__.__name__}[{as_path(path)}] is not assigned! ")
        return _not_found_

    def __contains__(self, path: PathLike) -> bool:
        """检查 path 是否存在"""
        return self.query(path, Query.tags.exists)

    def __equal__(self, other) -> bool:
        return self.query({Query.tags.equal: other})

    def __iter__(self) -> typing.Generator[_T, None, None]:
        """遍历子节点"""
        yield from self.children()

    def children(self) -> typing.Generator[HTreeNode | PrimaryType, None, None]:
        """遍历子节点 (for HTree)"""
        yield from self.search(["*"])

    def __len__(self) -> int:
        """返回子节点的数量"""
        return self.__find__(Query.tags.count)

    # -----------------------------------------------------------------------------
    # API as container

    def __as_node__(
        self, key, value, /, _type_hint=None, _entry=None, default_value=_not_found_, **kwargs
    ) -> typing.Self:
        if value is _not_found_ and _entry is None and default_value is not _not_found_:
            value = deepcopy(default_value)
            default_value = _not_found_

        if _type_hint is _not_found_:
            _type_hint = None

        if _type_hint is None and isinstance(key, str) and key.isidentifier():
            orig_cls = typing.get_origin(self.__class__) or self.__class__
            _type_hint = typing.get_type_hints(orig_cls).get(key, None)

        if _type_hint is None:
            _type_hint = getattr(self.__class__, "__args__", None)

        if isinstance(_type_hint, tuple):
            _type_hint = _type_hint[-1]

        if _type_hint is None and value is _not_found_ and _entry is not None:
            node = _entry.get()
            _entry = None

        elif isinstance(_type_hint, typing._GenericAlias):
            if issubclass(_type_hint.__origin__, HTreeNode):
                node = _type_hint(value, _entry=_entry, _parent=self, **kwargs)
            elif typing.get_origin(_type_hint) is tuple:
                if value is _not_found_ and _entry is not None:
                    value = _entry.get()
                if value is not _not_found_:
                    node = tuple(value)
                else:
                    node = _not_found_
            else:
                node = _type_hint(value)
        elif not inspect.isclass(_type_hint):
            node = value
        elif isinstance(value, _type_hint):
            node = value
        elif issubclass(_type_hint, HTreeNode):
            node = _type_hint(value, _entry=_entry, _parent=self, default_value=default_value, **kwargs)
        else:
            if _entry is not None:
                value = Path().update(value, _entry.get())
            node = type_convert(_type_hint, value, default_value=default_value)

        if isinstance(node, HTreeNode):
            if node._parent is None:
                node._parent = self

            if isinstance(key, str):
                node._metadata["name"] = key

            elif isinstance(key, int):
                node._metadata.setdefault("index", key)
                if self._metadata.get("name", _not_found_) in (_not_found_, None, "unnamed"):
                    self._metadata["name"] = str(key)

        if node is not _not_found_ and key is not None:
            self._cache = Path([key]).update(self._cache, node)

        return node

    def __get_node__(self, key, /, _type_hint=None, _entry=None, _getter=None, default_value=_not_found_, **kwargs):
        if key is None:
            return self

        value = Path([key]).find(self._cache, default_value=_not_found_)

        if value is _not_found_ and callable(_getter):
            value = _getter(self)

        # if value is _not_found_ or (isinstance(value, dict) and isinstance(default_value, dict)):
        #     value = Path().update(deepcopy(default_value), value)

        if _entry is None and self._entry is not None:
            _entry = self._entry.child(key)

        if default_value is not _not_found_:
            pass  # and _entry is not None:
        elif isinstance(key, int):
            default_value = self._metadata.get("default_value", _not_found_)
        else:
            default_value = Path([key]).get(self._metadata.get("default_value", _not_found_), _not_found_)

        node = self.__as_node__(key, value, _type_hint=_type_hint, _entry=_entry, default_value=default_value, **kwargs)

        return node

    def __set_node__(self, key, *args, _setter=None, **kwargs) -> None:
        if callable(_setter):
            _setter(self, key, *args, **kwargs)
        else:
            self._cache = Path([key] if key is not None else []).update(self._cache, *args, **kwargs)

        return self

    def __del_node__(self, key: str | int, _deleter=None) -> bool:
        if callable(_deleter):
            return _deleter(self, key)
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

    def __search__(self, predicate, *args, **kwargs) -> typing.Generator[HTreeNode, None, None]:
        cached_key = []
        for key, value in Path().search(self._cache, predicate, Query.tags.get_item):
            if isinstance(key, (str, int)):
                cached_key.append(key)
                entry = None if self._entry is None else self._entry.child(key)
                node = self.__as_node__(key, value, _entry=entry)
                yield Path().project(node, *args, **kwargs)
            else:
                yield Path().project(value, *args, **kwargs)

        if self._entry is not None:
            for key, entry in self._entry.search(predicate, Query.tags.get_item):
                if not isinstance(key, (str, int)) or key in cached_key:
                    continue
                node = self.__as_node__(key, _not_found_, _entry=entry)
                yield Path().project(node, *args, **kwargs)

        # if (self._cache is _not_found_ or len(self._cache) == 0) and self._entry is not None:
        #     for k, v in self._entry.search(path, **kwargs):
        #         if not isinstance(v, Entry):
        #             yield k, self._type_convert(v, k)
        #         else:
        #             yield k, self._type_convert(_not_found_, k, _entry=v)
        # elif self._cache is not None:
        #     for k, v in Path._search(self._cache, [], *args, **kwargs):
        #         _entry = self._entry.child(k) if self._entry is not None else None
        #         v = self._type_convert(v, k, _entry=_entry)
        #         yield k, v


class Dict(GenericHelper[_T], HTree):
    """Dict 类型的 HTree 对象"""

    def __init__(self, cache: typing.Any = _not_found_, /, **kwargs):
        d = {k: kwargs.pop(k) for k in list(kwargs.keys()) if not k.startswith("_")}
        cache = Path().update(cache, d)
        super().__init__(cache, **kwargs)

    @property
    def is_mapping(self) -> bool:
        """只读属性，返回节点是否为Mapping"""
        return True

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
        return len(self.keys())


collections.abc.MutableMapping.register(Dict)


class List(GenericHelper[_T], HTree):
    """List 类型的 HTree 对象"""

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], collections.abc.Sequence):
                cache = args[0]
            elif args[0] is _not_found_:
                cache = []
            else:
                raise TypeError(f"Invalid args {args}")
        else:
            cache = list(args)
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

    @typing.final
    def __iter__(self) -> typing.Generator[_T, None, None]:
        """遍历，sequence 返回子节点的值，mapping 返回子节点的键"""
        yield from self.search()

    def __get_node__(self, key, /, default_value=_not_found_, **kwargs) -> _T:
        if default_value is _not_found_:
            default_value = self._metadata.get("default_value", _not_found_)
        return super().__get_node__(key, default_value=default_value, **kwargs)

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
