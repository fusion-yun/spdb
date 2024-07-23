import typing

from spdm.core.history import WithHistory
from spdm.model.process import Process


class Actor(WithHistory, Process):
    """执行体，具有状态历史和空间区域的实体。"""

    def execute(self, *args, **kwargs) -> typing.Self:
        state = super().execute(*args, **kwargs)
        res = object.__new__(self.__class__)
        res.__setsate__(state)
        return res
