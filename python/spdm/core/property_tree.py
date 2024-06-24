from __future__ import annotations
import typing

from spdm.core.aos import AoS
from spdm.core.htree import HTree, Dict, List
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger


class PropertyTree(Dict):
    """属性树，通过 __getattr__ 访问成员，并转换为对应的类型"""

    def __getattr__(self, key: str) -> typing.Self | AoS[typing.Self]:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self.__get_node__(key, default_value=_not_found_)

    def __get_node__(self, key, *args, _type_hint=None, **kwargs):

        value = super().__get_node__(key, *args, **kwargs)
        if value.__class__ is HTree:
            value = self._entry.get()
            

        if value.__class__ is Dict:
            value.__class__ = PropertyTree
        elif value.__class__ is List:
            value.__class__ = AoS[PropertyTree]

        return value

    def __setattr__(self, key: str, value: typing.Any):
        if key.startswith("_"):
            return super().__setattr__(key, value)

        return self.__set_node__(key, value)
