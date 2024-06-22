""" Hierarchical Tree (HTree) is a hierarchical data structure that can be used to
 store a group of data or objects, such as lists, dictionaries, etc.  """

from __future__ import annotations
import collections.abc
import typing
import inspect
import abc

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, as_array, primary_type, PrimaryType, type_convert

from spdm.core.entry import Entry, open_entry
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
    """HTreeNode is a node in the hierarchical tree."""

    def __new__(cls, *args, **kwargs):
        if cls is not HTreeNode and cls is not HTree:
            return super().__new__(cls)
        elif len(args) == 0:
            return super().__new__(Dict)
        elif len(args) > 1:
            return super().__new__(List)

        value = args[0]

        if isinstance(value, collections.abc.Mapping):
            return super().__new__(Dict)
        elif isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
            return super().__new__(List)
        elif isinstance(value, HTreeNode):
            raise RuntimeError(f"Can not create {cls.__name__} from {value.__class__.__name__}")
        elif len(kwargs) == 0 and cls is not HTree:
            if not isinstance(value, primary_type) and not (value is None or value is _not_found_):
                raise TypeError(f"Can not create {cls.__name__} from '{value.__class__.__name__}'")
            return value
        else:
            return super().__new__(cls)

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
    def parent(self) -> HTreeNode:
        """父节点"""
        return self._parent

    @typing.final
    def ancestors(self) -> typing.Generator[HTreeNode, None, None]:
        """遍历祖辈节点"""
        obj = self._parent
        while obj is not None:
            yield obj
            obj = getattr(obj, "_parent", None)

    def children(self) -> typing.Generator[HTreeNode | PrimaryType, None, None]:
        """遍历子节点 (for HTree)"""

    @typing.final
    def descendants(self, traversal_strategy="deep_first") -> typing.Generator[HTreeNode, None, None]:
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
    def __value__(self) -> typing.Any:
        return self.read()

    def __array__(self) -> ArrayType:  # for numpy
        return as_array(self.read())

    def __null__(self) -> bool:
        """判断节点是否为空，若节点为空，返回 True，否则返回 False
        @NOTE 长度为零的 list 或 dict 不是空节点
        """
        return self._cache is None and self._entry is None

    def __empty__(self) -> bool:
        return (self._cache is _not_found_ or len(self._cache) == 0) and (self._entry is None)

    def __bool__(self) -> bool:
        return self.query({Path.tags.equal: True})

    def __equal__(self, other) -> bool:
        """比较节点的值是否相等"""
        return self.query({Path.tags.equal: other if not isinstance(other, HTreeNode) else other.__value__})

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


_T = typing.TypeVar("_T", *primary_type, HTreeNode)
_TR = typing.TypeVar("_TR")  # return value type


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
    def put(self, *args, **kwargs):
        """Put, alias of update"""
        return self.update(*args, **kwargs)

    @typing.final
    def get(self, path, default_value=None, **kwargs) -> _T:
        """Get , alias of query"""
        return self.query(path, default_value=default_value, **kwargs)

    @typing.final
    def pop(self, *args, default_value=_not_found_, **kwargs) -> typing.Any:
        """Pop , query and delete"""
        node = self.get(*args, default_value=_not_found_, **kwargs)
        if node is not _not_found_:
            self.delete(*args, **kwargs)
            return node
        else:
            return default_value

    @typing.final
    def search(self, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """搜索（Search ）符合条件节点或属性。查询是一个幂等操作，它不会改变树的状态。"""
        yield from Path(*args).search(self, **kwargs)

    @typing.final
    def traversal(self, *args, **kwargs) -> typing.Generator[_T, None, None]:
        """遍历（Traversal），遍历树中的子节点 。 alias of search
        - 返回一个迭代器，允许用户在遍历过程中处理每个节点。
        """
        yield from self.search(*args, **kwargs)

    @typing.final
    def find(self, *args, **kwargs) -> _T:
        """查找（Find)，返回第一个 search 结果"""
        return Path(*args[:1]).find(self, *args[1:], **kwargs)

    @typing.final
    def query(self, *args, **kwargs) -> _TR:
        """查询（Query）， args[-1] 为 projection"""
        return Path(*args[:1]).query(self, *args[1:], **kwargs)

    # @typing.final
    # def for_each(self, op: typing.Callable[[_T], _TR], **kwargs) -> typing.Generator[_TR, None, None]:
    #     """alias of search
    #     这通常是一个函数或方法，用于对集合中的每个元素执行某种操作。这个操作通常是由一个函数或者一个lambda表达式定义的。
    #     for_each不关心元素的顺序或者它们如何被存储，它只是简单地对每个元素执行相同的操作。"""
    #     yield from self.search(projection=projection, **kwargs)
    # @typing.final
    # def find_cache(self, path, *args, default_value=_not_found_, **kwargs) -> typing.Any:
    #     """find value from cache"""
    #     res = Path.do_find(self._cache, path, *args, default_value=_not_found_, **kwargs)
    #     if res is _not_found_ and self._entry is not None:
    #         res = self._entry.child(path).find(*args, default_value=_not_found_, **kwargs)
    #     if res is _not_found_:
    #         res = default_value
    #     return res

    # @typing.final
    # def get_cache(self, path, default_value=_not_found_) -> typing.Any:
    # """get value from cache"""
    # return self.find_cache(path, default_value=default_value)

    # Python special methods

    @typing.final
    def __getitem__(self, path: PathLike) -> _T:
        """Get item from tree by path. 当找不到时，调用 __missing__ 方法"""
        node = self.get(path, _not_found_)
        return node if node is not _not_found_ else self.__missing__(path)

    @typing.final
    def __setitem__(self, path: PathLike, value) -> None:
        """Set item to tree by path. alias of update"""
        return self.update(path, value)

    @typing.final
    def __delitem__(self, path: PathLike) -> None:
        """Delete item. alias of delete"""
        return self.delete(path)

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

    @abc.abstractmethod
    def __iter__(self) -> typing.Generator[_T, None, None]:
        """遍历子节点"""

    @abc.abstractmethod
    def children(self) -> typing.Generator[HTreeNode | PrimaryType, None, None]:
        """遍历子节点 (for HTree)"""

    @abc.abstractmethod
    def __len__(self) -> int:
        """返回子节点的数量"""

    # -----------------------------------------------------------------------------
    # API as container

    def __get_node__(self, key, *args, **kwargs) -> typing.Any:
        if key is None and len(args) + len(kwargs) == 0:
            return self

        value = Path([key]).find(self._cache, *args, **kwargs)

        entry = self._entry.child(key) if self._entry is not None else None

        type_hint = None

        if isinstance(key, str) and key.isidentifier():
            cls = typing.get_origin(self.__class__) or self.__class__
            type_hint = typing.get_type_hints(cls).get(key, None)

        if type_hint is None:
            type_hint = getattr(self.__class__, "__args__", None)

        if type_hint is None or type_hint is _not_found_:
            node = value

        else:
            if not isinstance(type_hint, tuple):
                type_hint = (type_hint,)
            for tp in type_hint:
                if not inspect.isclass(tp):
                    continue
                elif isinstance(value, tp):
                    node = value
                elif issubclass(tp, HTreeNode):
                    node = tp(value, _entry=entry, _parent=self)
                else:
                    node = type_convert(tp, value)
                break

        if isinstance(node, HTreeNode):
            if node._parent is None:
                node._parent = self

            if isinstance(key, str):
                node._metadata["name"] = key

            elif isinstance(key, int):
                node._metadata.setdefault("index", key)
                if self._metadata.get("name", _not_found_) in (_not_found_, None, "unnamed"):
                    self._metadata["name"] = str(key)

        return node

    def __set_node__(self, key, *args, **kwargs) -> None:
        self._cache = Path([key]).update(self._cache, *args, **kwargs)
        # key = args[0]
        # if (key is None or key == []) and value is self:
        #     pass

        # elif isinstance(key, str) and key.startswith("@"):
        #     value = Path._delete(self._metadata, key[1:], value, *args, **kwargs)

        # else:
        #     self._cache = Path._delete(self._cache, key, value, *args, **kwargs)

        return self
        # path = Path(*args)
        # if path.is_query:
        #     query = path.pop()
        # else:
        #     query = Path.tags.get
        # key = args[0]
        # if isinstance(key, str) and key.startswith("@"):
        #     value = Path.do_find(self._metadata, key[1:], *args, default_value=_not_found_)
        # else:
        #     if isinstance(key, int):
        #         if key < len(self._cache):
        #             value = self._cache[key]
        #         else:
        #             value = _not_found_
        #     else:
        #         value = Path.do_find(self._cache, key, default_value=_not_found_)
        #     _entry = self._entry.child(key) if self._entry is not None else None
        #     value = self._type_convert(value, key, _entry=_entry, default_value=default_value, **kwargs)
        #     if key is None and isinstance(self._cache, collections.abc.MutableSequence):
        #         self._cache.append(value)
        #     elif isinstance(key, str) and isinstance(self._cache, collections.abc.MutableSequence):
        #         self._cache = Path.do_update(self._cache, key, value)
        #     elif isinstance(key, int) and key <= len(self._cache):
        #         if self._cache is _not_found_:
        #             self._cache = []
        #         self._cache.extend([_not_found_] * (key - len(self._cache) + 1))
        #         self._cache[key] = value
        #     else:
        #         if not isinstance(self._cache, collections.abc.Mapping):
        #             self._cache = {}
        #         self._cache[key] = value
        # return value

    def __del_node__(self, key_or_index: str | int) -> bool:
        if (isinstance(self._cache, collections.abc.MutableMapping) and key_or_index in self._cache) or (
            isinstance(self._cache, collections.abc.Sequence) and key_or_index < len(self._cache)
        ):
            self._cache[key_or_index] = _not_found_
            return True
        else:
            return False

    def __query__(self, *args, **kwargs) -> typing.Any:
        res = Path(*args[:1]).query(self._cache, *args[1:], **kwargs)
        if res is _not_found_ and self._entry is not None:
            res = self._entry.child(*args[:1]).query(*args[1:], **kwargs)
        return res
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


class Dict(HTree[_T]):
    """Dict 类型的 HTree 对象"""

    def __init__(self, cache: typing.Any = _not_found_, /, _entry: Entry = None, _parent: HTreeNode = None, **kwargs):
        if cache is  _not_found_:
            cache = {}
        super().__init__(cache, _entry=_entry, _parent=_parent, **kwargs)

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


class List(HTree[_T]):
    """List 类型的 HTree 对象"""

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if args[0] is _not_found_:
                cache = []
            elif isinstance(args[0], list):
                cache = args[0]
            elif isinstance(args[0], collections.abc.Iterable):
                cache = [*args[0]]
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

    def __iadd__(self, other: list) -> typing.Type[List[_T]]:
        return self.extend(other)

    def __contains__(self, path_or_node: PathLike | HTreeNode) -> bool:
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
            yield self.__getchild__(idx)

    @typing.final
    def __iter__(self) -> typing.Generator[_T, None, None]:
        """遍历子节点"""
        yield from self.children()


collections.abc.MutableSequence.register(List)

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
