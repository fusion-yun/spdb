import uuid
from ..view import sp_view as sp_view

from .pluggable import Pluggable
from .sp_property import SpTree


class SpObject(SpTree, Pluggable):
    """对象的基类/抽象类

    Args:
        SpTree (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        SpTree.__init__(self, *args, **kwargs)
        self._uid = uuid.uuid3(uuid.uuid1(clock_seq=0), self.__class__.__name__)

    def _repr_svg_(self):
        return sp_view.display(self.__geometry__(), output="svg")

    def __geometry__(self):
        return None

    @property
    def uid(self) -> uuid.UUID:
        return self._uid

    def _plugin_path(self) -> str:
        return self.__module__ + "." + self.__class__.__name__
