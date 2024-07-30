import uuid
import typing

from spdm.core.sp_object import SpObject


class Entity(SpObject):
    """实体的基类/抽象类"""

    @property
    def uuid(self) -> uuid.UUID:
        if not hasattr(self, "_uuid"):
            self._uuid = uuid.uuid3(uuid.uuid1(clock_seq=0), self.__class__.__name__)
        return self._uuid

    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return getattr(self._parent, "context", None)

    def __view__(self, **kwargs) -> dict:
        return {"$styles": kwargs}
