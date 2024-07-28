""" Actor """

import typing
from spdm.model.process import Process


class Actor(Process):
    """执行体，具有状态历史和空间区域的实体。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._out_ports = self

    def execute(self, *args, **kwargs) -> typing.Self:
        """执行 Actor"""
        return self.__class__(super().execute(*args, **kwargs))
