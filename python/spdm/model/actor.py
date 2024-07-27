""" Actor """

import typing
from spdm.core.sp_tree import annotation
from spdm.model.process import Process


class Actor(Process):
    """执行体，具有状态历史和空间区域的实体。"""

    out_ports: typing.Self = annotation(alias="..")

    def execute(self, *args, **kwargs) -> typing.Self:
        """执行 Actor"""
        return self.__class__(super().execute(*args, **kwargs))
