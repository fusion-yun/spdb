import uuid
import typing

from spdm.core.htree import HTree
from ..view import sp_view as sp_view

from .pluggable import Pluggable
from .sp_property import SpTree


class SpObject(SpTree, Pluggable):
    """对象的基类/抽象类

    Args:
        SpTree (_type_): _description_
    """

    def __new__(cls, *args, **kwargs) -> typing.Type[typing.Self]:

        cls_name = args[0].get("$class", None) if len(args) == 1 and isinstance(args[0], dict) else None
        
        return super().__new__(cls, cls_name)

    @classmethod
    def __deserialize__(cls, desc: dict) -> typing.Type[HTree]:
        return cls.__new__(desc)

    def __init__(self, *args, **kwargs):
        SpTree.__init__(self, *args, **kwargs)
        self._uid = uuid.uuid3(uuid.uuid1(clock_seq=0), self.__class__.__name__)

    def _repr_svg_(self):
        return sp_view.display(self.__view__(), output="svg")

    def __view__(self):
        return None

    @property
    def uid(self) -> uuid.UUID:
        return self._uid
