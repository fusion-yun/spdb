import typing

from spdm.model.process import Process


class Actor(Process):
    """执行体，具有状态历史和空间区域的实体。"""

    def refresh(self, *args, **kwargs) -> typing.Self:
        super().refresh(*args, **kwargs)

        return self
