import typing

from spdm.utils.tags import _not_found_
from spdm.core.path import Path
from spdm.core.entry import as_entry
from spdm.core.htree import HTreeNode
from spdm.core.sp_tree import SpTree
from spdm.core.pluggable import Pluggable


class SpObject(Pluggable, SpTree):
    """SpObject 对象的基类
    =================================================
    - 对象工厂，根据输入参数生成对象

    """

    def __new__(cls, *args, plugin_name=None, _entry=None, **kwargs) -> typing.Self:
        if plugin_name is None:
            plugin_name = kwargs.pop("kind", None) or kwargs.pop("type", None)

            if plugin_name is None and len(args) > 0 and isinstance(args[0], dict):
                plugin_name = args[0].get("type", None)

            if plugin_name is None and _entry is not None:
                plugin_name = _entry.get("type", None)

        return super().__new__(cls, *args, _plugin_name=plugin_name, **kwargs)

    def __init__(self, *args, _entry=None, _parent=None, **kwargs):

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

        cache = Path().update(cache, kwargs)

        super().__init__(cache, _entry=as_entry(entries), _parent=_parent)

    name: str

    def __hash__(self) -> int:
        return hash(self.name)

    # def __copy__(self) -> typing.Self:
    #     return SpTree.__copy__(self)
