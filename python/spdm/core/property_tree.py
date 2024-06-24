from __future__ import annotations
import typing

from spdm.core.aos import AoS
from spdm.core.htree import HTree, Dict
from spdm.core.path import Path
from spdm.utils.tags import _not_found_


class PropertyTree(Dict):
    """属性树，通过 __getattr__ 访问成员，并转换为对应的类型"""

    def __getattr__(self, key: str) -> typing.Self | AoS[typing.Self]:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self.__get_node__(key, default_value=_not_found_)

    def __get_node__(self, key, *args, _type_hint=None, **kwargs):
        if _type_hint is None:
            _type_hint = self.__class__

        _entry = self._entry.child(key) if self._entry is not None else None

        value = Path([key]).get(self._cache, *args, **kwargs)

        if value is _not_found_ and _entry is not None:
            value = _entry.get(default_value=_not_found_)
            _entry = None

        if isinstance(value, dict) :
            value = PropertyTree(value, _entry=_entry, _parent=self)
        elif isinstance(value, list) and (len(value) == 0 or isinstance(value[0], (dict, HTree))):
            value = AoS[PropertyTree](value, _entry=_entry, _parent=self)
        elif value is _not_found_ and _entry is not None:
            value = PropertyTree(value, _entry=_entry, _parent=self)

        return value

    def __setattr__(self, key: str, value: typing.Any):
        if key.startswith("_"):
            return super().__setattr__(key, value)

        return self.__set_node__(key, value)
