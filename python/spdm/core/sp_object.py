import uuid
import typing


from .pluggable import Pluggable
from .sp_tree import SpTree, PropertyTree, sp_property


class SpObject(SpTree, Pluggable):
    """对象的基类/抽象类"""

    def __new__(cls, *args, **kwargs) -> typing.Type[typing.Self]:

        cls_name = (
            args[0].get("$class", None) if len(args) == 1 and isinstance(args[0], dict) else kwargs.get("plugin", None)
        )

        return super().__new__(cls, cls_name)

    def __init__(self, *args, **kwargs) -> None:
        SpTree.__init__(self, *args, **kwargs)

    @sp_property
    def metadata(self) -> PropertyTree:
        return self._metadata


import inspect

_T = typing.TypeVar("_T")

from .sp_tree import _process_sptree


def sp_object(cls: _T = None, /, **kwargs) -> _T:

    def wrap(_cls, _kwargs=kwargs):
        if not inspect.isclass(_cls):
            raise TypeError(f"Not a class {_cls}")

        if not issubclass(_cls, SpObject):
            n_cls = type(_cls.__name__, (_cls, SpObject), {})
            n_cls.__module__ = _cls.__module__
        else:
            n_cls = _cls

        n_cls = _process_sptree(n_cls, **_kwargs)

        return n_cls

    if cls is None:
        return wrap
    else:
        return wrap(cls)
