import typing
import inspect
from copy import copy


from spdm.utils.tags import _not_found_
from spdm.core.pluggable import Pluggable
from spdm.core.path import Path
from spdm.core.entry import as_entry
from spdm.core.htree import HTreeNode
from spdm.core.sp_tree import SpTree


class SpObject(Pluggable, SpTree):
    """SpObject 对象的基类
    =================================================
    - 对象工厂，根据输入参数生成对象

    """

    def __new__(cls, *args, _entry=None, **kwargs):
        if "_plugin_prefix" not in cls.__dict__:
            return super().__new__(cls, *args, _entry=_entry, **kwargs)

        plugin_name = kwargs.pop("type", None)

        if plugin_name is None and len(args) > 0 and isinstance(args[0], dict):
            plugin_name = args[0].get("type", None)

        if plugin_name is None and _entry is not None:
            plugin_name = _entry.get("type", None)

        return super().__new__(cls, *args, _plugin_name=plugin_name, _entry=_entry, **kwargs)

    def __init__(self, *args, _entry=None, **kwargs) -> None:
        kwargs.pop("type", None)
        entries = []
        cache = {}
        for a in args:
            if isinstance(a, HTreeNode):
                entries.append(a._entry)
                cache = Path().update(cache, a._cache)
            elif isinstance(a, dict):
                entries.append(a.pop("$entry", _not_found_))
                cache = Path().update(cache, a)
            elif a is not _not_found_:
                entries.append(a)

        entries.append(_entry)

        super().__init__(cache, _entry=as_entry(tuple(entries)), **kwargs)

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

    from spdm.core.sp_tree import _make_sptree

    def wrap(_cls, _kwargs=copy(kwargs)):
        if not inspect.isclass(_cls):
            raise TypeError(f"Not a class {_cls}")

        if not issubclass(_cls, SpObject):
            n_cls = type(_cls.__name__, (_cls, SpObject), {})
            n_cls.__module__ = _cls.__module__
        else:
            n_cls = _cls

        n_cls = _make_sptree(n_cls, **_kwargs)

        return n_cls

    return wrap if cls is None else wrap(cls)
