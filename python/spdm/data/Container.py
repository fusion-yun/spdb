import collections
import collections.abc
import dataclasses
import inspect
from functools import cached_property
from typing import Any, Generic, Iterator, TypeVar, Union, final, get_args, Mapping

import numpy as np

from ..common.logger import logger
from ..common.tags import _not_found_, _undefined_
from ..util.utilities import serialize
from .Entry import (Entry,   _next_, _TPath)
from .Node import Node
from .Path import Path

_TObject = TypeVar("_TObject")
_TContainer = TypeVar("_TContainer", bound="Container")
_T = TypeVar("_T")


class Container(Node, Generic[_TObject]):
    r"""
       Container Node
    """

    def __init__(self, *args,  **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        annotation = [f"{k}='{v}'" for k, v in self.annotation.items() if v is not None]
        return f"<{getattr(self,'__orig_class__',self.__class__.__name__)} {' '.join(annotation)}/>"

    def __serialize__(self) -> Any:
        return serialize(self._entry.dump())

    def _duplicate(self, *args, parent=None, **kwargs) -> _TContainer:
        return self.__class__(self._entry, *args, parent=parent if parent is not None else self._parent,  **kwargs)

    def __setitem__(self, key: Any, value: _T) -> _T:
        return self._entry.child(key).push(self._pre_process(value))

    def __getitem__(self, key: Any) -> Any:
        return self._post_process(self._entry.child(key), path=key)

    def __delitem__(self, key: Any) -> bool:
        return self._entry.child(key).erase()

    def __contains__(self, key: Any) -> bool:
        return self._entry.child(key).exists()

    def __eq__(self, other) -> bool:
        return self._entry.equal(other)

    def __len__(self) -> int:
        return self._entry.count()

    def __iter__(self) -> Iterator[_T]:
        for idx, obj in enumerate(self._entry):
            yield self._post_process(obj, path=[idx])

    def append(self, value) -> _TContainer:
        self._entry.push([value], extend=True)
        return self

    def extend(self, value) -> _TContainer:
        self._entry.push(value, extend=True)
        return self

    def __ior__(self, obj) -> _TContainer:
        self._entry.push(obj, update=True)
        return self

    def _pre_process(self, value: _T, *args, **kwargs) -> _T:
        return value

    def _post_process(self, value: _T, *args,   **kwargs) -> Union[_T, Node]:
        return Container.create(value, self, *args,  **kwargs)

    def _attribute_type(self, attribute=_undefined_):
        attr_type = _undefined_

        if isinstance(attribute, str):
            attr = dict(inspect.getmembers(self.__class__)).get(attribute, _not_found_)
            if isinstance(attr, (_sp_property, cached_property)):
                attr_type = attr.func.__annotations__.get("return", None)
            elif isinstance(attr, (property)):
                attr_type = attr.fget.__annotations__.get("return", None)
        elif attribute is _undefined_:
            child_cls = Node
            #  @ref: https://stackoverflow.com/questions/48572831/how-to-access-the-type-arguments-of-typing-generic?noredirect=1
            orig_class = getattr(self, "__orig_class__", None)
            if orig_class is not None:
                child_cls = get_args(self.__orig_class__)
                if child_cls is not None and len(child_cls) > 0 and inspect.isclass(child_cls[0]):
                    child_cls = child_cls[0]
            attr_type = child_cls
        else:
            raise NotImplementedError(attribute)

        return attr_type

    @classmethod
    def create(cls, value: _T, /, parent=_undefined_, type_hint=_undefined_, **kwargs) -> Union[_T, Node]:
        return Node.create(value, parent=parent, **kwargs)

        # elif (isinstance(value, list) and all(filter(lambda d: isinstance(d, (int, float, np.ndarray)), value))):
        #     return value
        # elif inspect.isclass(self._new_child):
        #     if isinstance(value, self._new_child):
        #         return value
        #     elif issubclass(self._new_child, Node):
        #         return self._new_child(value, parent=parent, **kwargs)
        #     else:
        #         return self._new_child(value, **kwargs)
        # elif callable(self._new_child):
        #     return self._new_child(value, **kwargs)
        # elif isinstance(self._new_child, collections.abc.Mapping) and len(self._new_child) > 0:
        #     kwargs = collections.ChainMap(kwargs, self._new_child)
        # elif self._new_child is not _undefined_ and not not self._new_child:
        #     logger.warning(f"Ignored!  { (self._new_child)}")

        # if isinstance(attribute, str) or attribute is _undefined_:
        #     attribute_type = self._attribute_type(attribute)
        # else:
        #     attribute_type = attribute

        # if inspect.isclass(attribute_type):
        #     if isinstance(value, attribute_type):
        #         res = value
        #     elif attribute_type in (int, float):
        #         res = attribute_type(value)
        #     elif attribute_type is np.ndarray:
        #         res = np.asarray(value)
        #     elif dataclasses.is_entryclass(attribute_type):
        #         if isinstance(value, collections.abc.Mapping):
        #             res = attribute_type(
        #                 **{k: value.get(k, None) for k in attribute_type.__entryclass_fields__})
        #         elif isinstance(value, collections.abc.Sequence):
        #             res = attribute_type(*value)
        #         else:
        #             res = attribute_type(value)
        #     elif issubclass(attribute_type, Node):
        #         res = attribute_type(value, parent=parent, **kwargs)
        #     else:
        #         res = attribute_type(value, **kwargs)
        # elif hasattr(attribute_type, '__origin__'):
        #     if issubclass(attribute_type.__origin__, Node):
        #         res = attribute_type(value, parent=parent, **kwargs)
        #     else:
        #         res = attribute_type(value, **kwargs)
        # elif callable(attribute_type):
        #     res = attribute_type(value, **kwargs)
        # elif attribute_type is not _undefined_:
        #     raise TypeError(attribute_type)

    # @property
    # def entry(self) -> Entry:
    #     return self._entry

    # def __ior__(self,  value: _T) -> _T:
    #     return self._entry.push({Entry.op_tag.update: value})

    # @property
    # def _is_list(self) -> bool:
    #     return False

    # @property
    # def _is_dict(self) -> bool:
    #     return False

    # @property
    # def is_valid(self) -> bool:
    #     return self._entry is not None

    # def flush(self):
    #     if self._entry.level == 0:
    #         return
    #     elif self._is_dict:
    #         self._entry.moveto([""])
    #     else:
    #         self._entry.moveto(None)

    # def clear(self):
    #     self._entry.push(Entry.op_tag.reset)

    # def remove(self, path: _TPath = None) -> bool:
    #     return self._entry.push(path, Entry.op_tag.remove)

    # def reset(self, cache=_undefined_, ** kwargs) -> None:
    #     if isinstance(cache, Entry):
    #         self._entry = cache
    #     elif cache is None:
    #         self._entry = None
    #     elif cache is not _undefined_:
    #         self._entry = Entry(cache)
    #     else:
    #         self._entry = Entry(kwargs)

    # def update(self, value: _T, **kwargs) -> _T:
    #     return self._entry.push([], {Entry.op_tag.update: value}, **kwargs)

    # def find(self, query: _TPath, **kwargs) -> _TObject:
    #     return self._entry.pull({Entry.op_tag.find: query},  **kwargs)

    # def try_insert(self, query: _TPath, value: _T, **kwargs) -> _T:
    #     return self._entry.push({Entry.op_tag.try_insert: {query: value}},  **kwargs)

    # def count(self, query: _TPath, **kwargs) -> int:
    #     return self._entry.pull({Entry.op_tag.count: query}, **kwargs)

    # # def dump(self) -> Union[Sequence, Mapping]:
    # #     return self._entry.pull(Entry.op_tag.dump)

    # def put(self, path: _TPath, value, *args, **kwargs) -> _TObject:
    #     return self._entry.put(path, value, *args, **kwargs)

    # def get(self, path: _TPath, *args, **kwargs) -> _TObject:
    #     return self._entry.get(path, *args, **kwargs)

    # def replace(self, path, value: _T, *args, **kwargs) -> _T:
    #     return self._entry.replace(path, value, *args, **kwargs)


    # def equal(self, path: _TPath, other) -> bool:
    #     return self._entry.pull(path, {Entry.op_tag.equal: other})
Node._CONTAINER_TYPE_ = Container[Node]
