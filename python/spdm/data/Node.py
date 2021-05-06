import collections
import copy
import functools
import inspect
import pprint
import typing
from enum import IntFlag
from functools import cached_property
from typing import Mapping, Sequence, TypeVar, Iterator, MutableMapping, MutableSequence, get_args
import numpy as np

from ..util.logger import logger
from ..util.utilities import try_get, serialize
from .Entry import _NEXT_TAG_, Entry, _last_, _next_, _not_found_

_TObject = TypeVar('_TObject')
_TKey = TypeVar('_TKey', int, str)
_TIndex = TypeVar('_TIndex', int, slice, _NEXT_TAG_)


class Node:
    r"""
        @startuml

        class Node{
            name    : String
            parent  : Node
            value   : Group or Data
        }

        class Group{
            children : Node[*]
        }

        Node *--  Node  : parent

        Node o--  Group : value
        Node o--  Data  : value

        Group *-- "*" Node

        @enduml
    """
    __slots__ = "_parent", "_cache", "_default_factory", "__orig_class__"

    class LazyHolder:
        __slots__ = "_prefix", "_parent"

        def __init__(self, parent, path, prefix=[]) -> None:
            self._parent = parent
            if isinstance(path, str):
                self._prefix = (prefix or []) + path.split('.')
            elif isinstance(path, collections.abc.MutableSequence):
                self._prefix = (prefix or []) + path
            else:
                self._prefix = (prefix or []) + [path]

        @property
        def parent(self):
            return self._parent

        @property
        def prefix(self):
            return self._prefix

        def extend(self, path):
            return self if path is None else Node.LazyHolder(self._parent, path, prefix=self._prefix)

    def __init__(self, data=None, *args, default_factory=None, parent=None, **kwargs):
        super().__init__()
        self._parent = parent
        self._cache = data._cache if isinstance(data, Node) else data
        self._default_factory = default_factory

    def __repr__(self) -> str:
        # d = f"<LazyHolder  prefix='{self._cache.prefix}' />" if isinstance(self._cache, Node.LazyHolder) else self._cache
        # return pprint.pformat(self.__serialize__())
        return f"<{self.__class__.__name__} />"

    # def copy(self):
    #     if isinstance(Node, (Node.Mapping, Node.Sequence)):
    #         return self.__new_child__(self._cache.copy())
    #     else:
    #         return self.__new_child__(copy.copy(self._cache))

    def __serialize__(self):
        return serialize(self._cache)

    # @staticmethod
    # def deserialize(cls, d):
    #     return cls(d)

    def __fetch__(self):
        if isinstance(self._cache, Entry):
            self._cache = self._cache.get_value([])
        elif isinstance(self._cache, Node.LazyHolder):
            self._cache = self.__raw_get__([])

        return self._cache

    @property
    def __parent__(self):
        return self._parent

    def __hash__(self) -> int:
        return hash(self._name)

    def __clear__(self):
        self._cache = None

    class Category(IntFlag):
        UNKNOWN = 0
        ITEM = 0x000
        DICT = 0x100
        LIST = 0x200
        ENTRY = 0x400

        ARRAY = 0x010

        INT = 0x001
        FLOAT = 0x002
        COMPLEX = 0x004
        STRING = 0x008

    @staticmethod
    def __type_category__(d) -> IntFlag:
        flag = Node.Category.UNKNOWN
        if isinstance(d, (Entry, Node.LazyHolder)):
            flag |= Node.Category.ENTRY
        elif isinstance(d, np.ndarray):
            flag |= Node.Category.ARRAY
            if np.issubdtype(d.dtype, np.int64):
                flag |= Node.Category.INT
            elif np.issubdtype(d.dtype, np.float64):
                flag |= Node.Category.FLOAT
        elif isinstance(d, collections.abc.Mapping):
            flag |= Node.Category.DICT
        elif isinstance(d, collections.abc.Sequence):
            flag |= Node.Category.LIST
        elif isinstance(d, int):
            flag |= Node.Category.INT
        elif isinstance(d, float):
            flag |= Node.Category.FLOAT
        elif isinstance(d, str):
            flag |= Node.Category.STRING

        return flag

    """
        @startuml
        [*] --> Empty
        Empty       --> Sequence        : as_sequence, __update__(list), __setitem__(int,v),__getitem__(int)
        Empty       --> Mapping         : as_mapping , __update__(dict), __setitem__(str,v),__getitem__(str)
        Empty       --> Empty           : clear


        Item        --> Item            : "__fetch__"
        Item        --> Empty           : clear
        Item        --> Sequence        : __setitem__(_next_,v),__getitem__(_next_),as_sequence
        Item        --> Illegal         : as_mapping

        Sequence    --> Empty           : clear
        Sequence    --> Sequence        : as_sequence
        Sequence    --> Illegal         : as_mapping

        Mapping     --> Empty           : clear
        Mapping     --> Mapping         : as_mapping
        Mapping     --> Sequence        :  __setitem__(_next_,v),__getitem__(_next_),as_sequence


        Illegal     --> [*]             : Error

        @enduml
    """
    @property
    def __category__(self):
        return Node.__type_category__(self._cache)

    def __new_child__(self, value, *args, parent=None,  **kwargs):
        if self._default_factory is None and hasattr(self, "__orig_class__") and self.__orig_class__ is not None:
            #  @ref: https://stackoverflow.com/questions/48572831/how-to-access-the-type-arguments-of-typing-generic?noredirect=1
            factory = get_args(self.__orig_class__)
            if len(factory) > 0:
                factory = factory[-1]
            if not (inspect.isclass(factory) or callable(factory)):
                # logger.error(f"Illegal factory type! {factory}")
                factory = Node
            self._default_factory = factory

        if self._default_factory is not None:
            value = self._default_factory(value, *args,  parent=parent or self, ** kwargs)

        if isinstance(value, Node):
            pass
        elif isinstance(value, collections.abc.MutableSequence):
            value = List[_TObject](value, *args,
                                   parent=parent or self,
                                   #    default_factory=default_factory,
                                   **kwargs)
        elif isinstance(value, collections.abc.MutableMapping):
            value = Dict[_TKey, _TObject](value, *args,
                                          parent=parent or self,
                                          #   default_factory=default_factory,
                                          **kwargs)
        elif isinstance(value, (Entry, Node.LazyHolder)):
            value = Node(value, *args,
                         parent=parent or self,
                         #  default_factory=default_factory,
                         **kwargs)

        # else:  # if isinstance(value, (str, int, float, np.ndarray)) or value is None:
        return value

    def __pre_process__(self, value, *args, **kwargs):
        return value

    def __post_process__(self, value, *args,   **kwargs):
        return value if isinstance(value, Node) else self.__new_child__(value, *args, **kwargs)

    def __raw_set__(self, key, value):
        if isinstance(self._cache, Entry):
            return self._cache.insert(key, value)
        elif key is None and self._cache is None:
            self._cache = value
            return self._cache

        if isinstance(self._cache, Node.LazyHolder):
            entry = self._cache.extend(key)
            holder = entry.parent
            path = entry.prefix
        else:
            holder = self
            path = key

        if isinstance(path, str):
            path = path.split(".")
        elif not isinstance(path, collections.abc.MutableSequence):
            path = [path]

        if path is None or len(path) == 0:
            holder._cache = value
            return

        if holder._cache is None:
            if isinstance(path[0], str):
                holder._cache = Dict(parent=self)
            else:
                holder._cache = List(parent=self)

        obj = holder._cache

        for idx, key in enumerate(path[:-1]):

            child = {} if isinstance(path[idx+1], str) else []
            if isinstance(obj, Node):
                child = obj.__new_child__(child, parent=obj)
                obj = obj._cache

            if isinstance(obj, collections.abc.Mapping):
                if not isinstance(key, str):
                    raise TypeError(f"mapping indices must be str, not {type(key).__name__}")
                tmp = obj.setdefault(key, child)
                if tmp is None:
                    obj[key] = child
                    tmp = obj[key]
                obj = tmp
            elif isinstance(obj, collections.abc.MutableSequence):
                if isinstance(key, _NEXT_TAG_):
                    obj.append(child)
                    obj = obj[-1]
                elif isinstance(key, (int, slice)):
                    tmp = obj[key]
                    if tmp is None:
                        obj[key] = child
                        obj = obj[key]
                    else:
                        obj = tmp
                else:
                    raise TypeError(f"list indices must be integers or slices, not {type(key).__name__}")

            else:
                raise TypeError(f"Can not insert data to {path[:idx]}! type={type(obj)}")

        if isinstance(path[-1], _NEXT_TAG_):
            obj.append(value)
        else:
            obj[path[-1]] = value

    def __raw_get__(self, path):
        if isinstance(path, str):
            path = path.split(".")
        elif isinstance(path, _NEXT_TAG_):
            self.__raw_set__(_next_, None)
            return self.__raw_get__(-1)
        elif not isinstance(path, collections.abc.MutableSequence):
            path = [path]

        if path is None or (isinstance(path, collections.abc.MutableSequence) and len(path) == 0):
            return self._cache
        elif isinstance(self._cache, Node.LazyHolder):
            return self._cache.extend(path)
        elif self._cache is None:
            return Node.LazyHolder(self, path)
        obj = self

        for idx, key in enumerate(path):
            if isinstance(obj, Node):
                obj = obj._cache

            if isinstance(obj, Entry):
                obj = obj.get(path[idx:])
                break
            elif obj is _not_found_:
                # raise KeyError(f"{path[idx:]}")
                break
            elif key is None or key == "":
                pass
            # elif isinstance(key, _NEXT_TAG_):
            #     obj[_next_] = None
            #     obj = obj[-1]
            elif isinstance(obj, collections.abc.Mapping):
                if not isinstance(key, str):
                    raise TypeError(f"mapping indices must be str, not {type(key).__name__}! \"{key}\"")
                obj = obj.get(key, _not_found_)
            elif isinstance(obj, collections.abc.MutableSequence):
                if not isinstance(key, (int, slice)):
                    raise TypeError(f"list indices must be integers or slices, not {type(key).__name__}! \"{key}\"")
                elif isinstance(key, int) and key > len(self._cache):
                    raise IndexError(f"Out of range! {key} > {len(self._cache)}")
                obj = obj[key]
            else:
                obj = _not_found_

        if obj is _not_found_:
            return Node.LazyHolder(self, path)
        else:
            return obj

    def __setitem__(self, path, value):
        self.__raw_set__(path, self.__pre_process__(value))

    def __getitem__(self, path):
        return self.__post_process__(self.__raw_get__(path))

    def __delitem__(self, path):
        if isinstance(self._cache, Entry):
            self._cache.delete(path)
        elif not path:
            self.__clear__()
        elif not isinstance(self._cache, (collections.abc.Mapping, collections.abc.MutableSequence)):
            raise TypeError(type(self._cache))
        else:
            del self._cache[path]

    def __contains__(self, path):
        if isinstance(self._cache, Entry):
            return self._cache.contains(path)
        elif isinstance(path, str) and isinstance(self._cache, collections.abc.Mapping):
            return path in self._cache
        elif not isinstance(path, str):
            return path >= 0 and path < len(self._cache)
        else:
            return False

    def __len__(self):
        if isinstance(self._cache, Entry):
            return self._cache.count()
        elif isinstance(self._cache,  (collections.abc.Mapping, collections.abc.MutableSequence)):
            return len(self._cache)
        else:
            return 0 if self._cache is None else 1

    def __iter__(self):
        if isinstance(self._cache, Entry):
            yield from self._cache.iter()
        else:
            d = self.__fetch__()
            if isinstance(d, (collections.abc.MutableSequence)):
                yield from map(lambda v: self.__post_process__(v), d)
            elif isinstance(d, collections.abc.Mapping):
                yield from d

            else:
                yield self.__post_process__(d)

    def __eq__(self, other) -> bool:
        if isinstance(other, Node):
            other = other._cache

        if isinstance(self._cache, Entry):
            return self.equal(other)
        elif isinstance(self._cache, Node.LazyHolder):
            return other is None
        else:
            return self._cache == other

    def __bool__(self) -> bool:
        return False if isinstance(self._cache, Node.LazyHolder) else (not not self._cache)


class List(Node, MutableSequence[_TObject]):
    __slots__ = ()

    def __init__(self, d: collections.abc.Sequence = [], *args,   **kwargs):
        Node.__init__(self, d or [], *args,   **kwargs)

    def __serialize__(self):
        return [serialize(v) for v in self]

    @property
    def __category__(self):
        return super().__category__() | Node.Category.LIST

    def __len__(self) -> int:
        return Node.__len__(self)

    def __new_child__(self, value, *args, parent=None,  **kwargs):
        return super().__new_child__(value, *args, parent=parent or self._parent, **kwargs)

    def __setitem__(self, k: _TIndex, v: _TObject) -> None:
        self.__raw_set__(k, self.__pre_process__(v))

    def __getitem__(self, k: _TIndex) -> _TObject:
        obj = self.__raw_get__(k)
        orig_class = get_args(self.__orig_class__)
        if len(orig_class) > 0 and not isinstance(obj, orig_class[0]):
            obj = self.__post_process__(self.__raw_get__(k), parent=self._parent)
            self.__raw_set__(k, obj)
        return obj

    def __delitem__(self, k: _TIndex) -> None:
        Node.__delitem__(self, k)

    def __iter__(self):
        if isinstance(self._cache, (collections.abc.MutableSequence)):
            yield from map(lambda v: self.__post_process__(v), self._cache)
        elif isinstance(self._cache, collections.abc.Mapping):
            yield from self._cache
        else:
            yield from Node.__iter__(self)

    def insert(self, *args, **kwargs):
        return Node.__raw_set__(self, *args, **kwargs)


class Dict(MutableMapping[_TKey, _TObject], Node):
    __slots__ = ()

    def __init__(self, data: Mapping = {}, *args,  **kwargs):
        Node.__init__(self, data, *args, **kwargs)

    def __serialize__(self):
        cls = self.__class__
        res = {}
        for k in filter(lambda k: k[0] != '_', self.__dir__()):
            prop = getattr(cls, k, None)
            if isinstance(prop, (property, cached_property)):
                v = getattr(self, k, None)
            elif inspect.isfunction(prop):
                continue
            else:
                v = getattr(self, k, None)
            res[k] = v

        if isinstance(self._cache, (collections.abc.Mapping, Entry)):
            for k in filter(lambda k: k not in res and k[0] != '_', self._cache):
                res[k] = self._cache[k]

        return {k: serialize(v) for k, v in res.items() if isinstance(v, (int, float, str, collections.abc.Mapping, collections.abc.Sequence))}

    @classmethod
    def __deserialize__(cls, desc: Mapping):
        ids = desc.get("@ids", None)
        if ids is None:
            raise ValueError(desc)
        else:
            raise NotImplementedError(ids)

    @property
    def __category__(self):
        return super().__category__ | Node.Category.LIST

    def get(self, key: _TKey, default_value=None) -> _TObject:
        try:
            res = self.__raw_get__(key)
        except KeyError:
            res = default_value
        return self.__post_process__(res)

    def __getitem__(self, key: _TKey) -> _TObject:
        return self.__post_process__(self.__raw_get__(key))

    def __setitem__(self, key: _TKey, value: _TObject) -> None:
        self.__raw_set__(key, self.__pre_process__(value))

    def __delitem__(self, key: _TKey) -> None:
        return Node.__delitem__(self, key)

    def __iter__(self) -> Iterator[Node]:
        yield from Node.__iter__(self)

    def __len__(self) -> int:
        return Node.__len__(self)

    def __eq__(self, o: object) -> bool:
        return Node.__eq__(self, o)

    def __contains__(self, o: object) -> bool:
        return Node.__contains__(self, o)

    def __ior__(self, other):
        if self._cache is None:
            self._cache = other
        elif isinstance(self._cache, Node.LazyHolder):
            self.__raw_set__(None, other)
        elif isinstance(self._cache, collections.abc.Mapping):
            for k, v in other.items():
                self.__setitem__(k, v)
        else:
            raise TypeError(f"{type(other)}")

    def __iter__(self):
        return super().__iter__()
