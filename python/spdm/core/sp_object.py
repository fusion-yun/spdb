import typing
import inspect
from copy import copy

# from functools import cache


from spdm.core.pluggable import Pluggable
from spdm.core.sp_tree import SpTree

# from spdm.core.property_tree import PropertyTree


class SpObject(Pluggable, SpTree):
    """对象的基类/抽象类"""

    def __new__(cls, *args, _entry=None, **kwargs):
        _plugin_name = kwargs.pop("type", None)

        if _plugin_name is None and len(args) > 0 and isinstance(args[0], dict):
            _plugin_name = args[0].get("type", None) or args[0].get("@type", None) or args[0].get("@class", None)

        if _plugin_name is None and _entry is not None:
            _plugin_name = _entry.get("type", None) or _entry.get("@type", None) or _entry.get("@class", None)

        return super().__new__(cls, *args, _plugin_name=_plugin_name, _entry=_entry, **kwargs)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __copy__(self) -> typing.Self:
        return SpTree.__copy__(self)

    # @property
    # @cache
    # def metadata(self):
    #     """
    #     Return the metadata.

    #     Returns:
    #         PropertyTree: The metadata.
    #     """
    #     return PropertyTree(self._metadata)


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
