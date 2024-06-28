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

    def __new__(cls, *args, plugin_name=None, **kwargs):

        # if len(args) + len(kwargs) == 0 or (len(args) == 1 and args[0] is None):
        #     return object.__new__(cls)

        # if len(args) > 0 and isinstance(args[0], str):
        #     plugin_name = args[0]
        # else:
        #     if len(args) > 0 and isinstance(args[0], dict):
        #         desc = collections.ChainMap(kwargs, args[0])
        #     else:
        #         desc = kwargs

        #     for pth in map(as_path, cls._PLUGIN_TAGS):
        #         plugin_name = pth.get(desc, None)
        #         if plugin_name is None and _entry is not None:
        #             plugin_name = _entry.get(pth, None)

        #         if plugin_name is not None and plugin_name is not _not_found_:
        #             break

        return super().__new__(cls, plugin_name)

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
