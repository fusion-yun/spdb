from __future__ import annotations
import typing

from spdm.core.htree import HTree, List
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import primary_type


class PropertyTree(HTree):
    """属性树，通过 __getattr__ 访问成员，并转换为对应的类型"""

    def __as_node__(
        self, key, value, /, _entry=None, default_value=_not_found_, **kwargs
    ) -> typing.Self | List[typing.Self]:

        if value is _not_found_ and _entry is None:
            value = default_value

        if value is _not_found_ and _entry is None:
            node = _not_found_
        elif value is _not_found_ and _entry.is_list:
            node = List[PropertyTree](_not_found_, _entry=_entry, default_value=default_value, **kwargs)
        elif value is _not_found_ and _entry.is_dict:
            node = PropertyTree(_not_found_, _entry=_entry, default_value=default_value, **kwargs)
        elif value is _not_found_:
            value= _entry.get()
            node = self.__as_node__(key, value, _entry=None, default_value=default_value, **kwargs)
        elif isinstance(value, list) and (len(value) == 0 or any(not isinstance(v, primary_type) for v in value)):
            node = List[PropertyTree](value)
        elif isinstance(value, dict):
            node = PropertyTree(value)
        elif value.__class__ is HTree:
            value.__class__ = PropertyTree
            node = value
        else:
            node = value

        if isinstance(node, HTree):
            node._parent = self
            node._metadata["name"] = key

        return node

    def __getattr__(self, key: str) -> typing.Self | List[typing.Self]:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self.__get_node__(key, default_value=_not_found_)

    def __setattr__(self, key: str, value: typing.Any):
        if key.startswith("_"):
            return super().__setattr__(key, value)

        return self.__set_node__(key, value)
