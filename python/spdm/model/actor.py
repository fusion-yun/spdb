import typing

from spdm.utils.logger import logger
from spdm.utils.envs import SP_DEBUG, SP_LABEL


from spdm.model.port import Ports
from spdm.model.entity import Entity


class Actor(Entity):
    """执行体，具有状态历史和空间区域的实体。"""

    in_ports: Ports
    """输入的 Edge，记录对其他 Actor 的依赖。"""

    def initialize(self, *args, **kwargs) -> None:
        """初始化 Actor 。"""
        self.in_ports.connect(self.context)

    def advance(self, *args, **kwargs) -> typing.Self:
        """推进到下一个时间片，时间为 time"""
        # return super().advance(*args, **kwargs)

    def refresh(self, *args, **kwargs) -> typing.Self:
        """更新当前时间片 （time_slice）"""
        # return super().refresh(*args, **kwargs)

    def fetch(self, *args, **kwargs) -> typing.Any:
        return None
