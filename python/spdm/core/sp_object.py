import typing
import inspect
from copy import copy


from spdm.utils.tags import _not_found_
from spdm.core.pluggable import Pluggable
from spdm.core.entry import as_entry
from spdm.core.htree import HTree
from spdm.core.sp_tree import SpTree


class SpObject(Pluggable, SpTree):
    """SpObject 对象的基类
    =================================================
    - 对象工厂，根据输入参数生成对象

    """

    def __new__(cls, cache=_not_found_, _entry=None, **kwargs):
        plugin_name = kwargs.pop("type", None)

        if plugin_name is None and isinstance(cache, dict):
            plugin_name = cache.get("type", None) or cache.get("@type", None)

        if plugin_name is None and _entry is not None:
            plugin_name = _entry.get("type", None) or _entry.get("@type", None)
        if not isinstance(plugin_name, str) and plugin_name is not None:
            raise TypeError(plugin_name)
        return super().__new__(cls, cache, _plugin_name=plugin_name, _entry=_entry, **kwargs)

    def __init__(self, cache=_not_found_, _entry=None, **kwargs) -> None:
        entries = []
        if isinstance(cache, HTree):
            if cache._entry is not None:
                entries.append(cache._entry)
            cache = copy(cache._cache)
        elif isinstance(cache, dict):
            pass
        elif cache is not _not_found_:
            _entry = as_entry(tuple([cache, _entry]))
            cache = _not_found_

        super().__init__(cache, _entry=_entry, **kwargs)

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
