from __future__ import annotations
import inspect
import typing
from copy import deepcopy
from _thread import RLock

from spdm.core.entry import Entry
from spdm.core.aos import AoS
from spdm.core.htree import HTree, Dict, HTreeNode
from spdm.core.path import update_tree, Path
from spdm.core.sp_tree import SpTree
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_, _undefined_

_Ts = typing.TypeVarTuple("_Ts")
_T = typing.TypeVar("_T")


class PropertyTree(SpTree[_T, *_Ts]):
    """属性树，通过 __getattr__ 访问成员，并转换为对应的类型"""

    def __new__(cls, *args, **kwargs):
        if cls is PropertyTree and len(args) == 1 and not isinstance(args[0], (dict, Entry)):
            return args[0]
        else:
            return super().__new__(cls)

    def __getattr__(self, key: str, *args, **kwargs) -> typing.Self | AoS[typing.Self]:
        if key.startswith("_"):
            return super().__getattribute__(key)

        _entry = self._entry.child(key) if self._entry is not None else None
        value = Path([key]).get(self._cache, *args, **kwargs)
        if value is _not_found_ and _entry is not None:
            value = _entry.get(default_value=_not_found_)
            _entry = None

        if isinstance(value, dict):
            return PropertyTree(value, _entry=_entry, _parent=self)
        elif isinstance(value, list) and (len(value) == 0 or isinstance(value[0], (dict, HTree))):
            return AoS[PropertyTree](value, _entry=_entry, _parent=self)
        elif value is _not_found_:
            if _entry is not None:
                return PropertyTree(value, _entry=_entry, _parent=self)
            else:
                return self.__missing__(key)
        else:
            return value

    def __missing__(self, key) -> typing.Any:
        return _not_found_

    def _type_hint_(self, *args, **kwargs):
        return PropertyTree

    # def _type_convert(self, value: typing.Any, *args, _type_hint=None, **kwargs) -> _T:
    #     if _type_hint is None or _type_hint is _not_found_:
    #         return value
    #     else:
    #         return super()._type_convert(value, *args, _type_hint=_type_hint, **kwargs)

    def dump(self, entry: Entry | None = None, force=False, quiet=True) -> Entry:
        """
        Dumps the cache entries into an Entry object.

        Args:
            entry (Entry | None): An optional Entry object to update with the cache entries.
                If None, a deepcopy of the cache entries is returned.
            force (bool): If True, forces the update of the entry with the cache entries.
            quiet (bool): If True, suppresses any output during the update.

        Returns:
            Entry: The updated Entry object if entry is not None, otherwise a deepcopy of the cache entries.
        """
        if entry is None:
            return deepcopy(self._cache)
        else:
            entry.update(self._cache)
            return entry
