import uuid

from spdm.core.sp_object import SpObject


class Entity(SpObject):
    """实体的基类/抽象类"""

    @property
    def uuid(self) -> uuid.UUID:
        if not hasattr(self, "_uuid"):
            self._uuid = uuid.uuid3(uuid.uuid1(clock_seq=0), self.__class__.__name__)
        return self._uuid

    def _repr_svg_(self):
        from spdm.view import sp_view as sp_view

        return sp_view.display(self.__view__(), output="svg")

    def __view__(self):
        return None
