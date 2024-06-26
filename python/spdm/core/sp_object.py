import typing
import inspect
from copy import copy
from functools import cache

from spdm.core.pluggable import Pluggable
from spdm.core.sp_tree import SpTree
from spdm.core.property_tree import PropertyTree


class SpObject(SpTree, Pluggable):
    """对象的基类/抽象类"""

    _PLUGIN_TAGS = ("$class", "@class", "class", "$type", "@type", "type", "plugin")

    @property
    @cache
    def metadata(self):
        """
        Return the metadata.

        Returns:
            PropertyTree: The metadata.
        """
        return PropertyTree(self._metadata)


_T = typing.TypeVar("_T")


def sp_object(cls: _T = None, /, **kwargs) -> _T:
    """
    Decorator to convert cls into SpObject.

    Args:
        cls: The class to be converted.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        _T: The converted class.
    """

    from spdm.core.sp_tree import _process_sptree

    def wrap(_cls, _kwargs=copy(kwargs)):
        if not inspect.isclass(_cls):
            raise TypeError(f"Not a class {_cls}")

        if not issubclass(_cls, SpObject):
            n_cls = type(_cls.__name__, (_cls, SpObject), {})
            n_cls.__module__ = _cls.__module__
        else:
            n_cls = _cls

        n_cls = _process_sptree(n_cls, **_kwargs)

        return n_cls

    return wrap if cls is None else wrap(cls)
