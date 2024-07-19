import typing

from spdm.utils.logger import logger
from spdm.utils.envs import SP_DEBUG, SP_LABEL


from spdm.model.port import Ports
from spdm.model.entity import Entity


class Actor(Entity):
    """执行体，具有状态历史和空间区域的实体。"""

    class InPorts(Ports):
        """输入端口集合。"""

        pass

    in_ports: InPorts
    """输入的 Edge，记录对其他 Actor 的依赖。"""

    @property
    def out_port(self) -> typing.Self:
        return self

    def initialize(self, *args, **kwargs) -> None:
        """初始化 Actor 。"""
        super().__setstate__(*args, **kwargs)
        self.in_ports.connect(self.context)

    def refresh(self, *args, **kwargs):
        self.__setstate__(self.execute(*args, **kwargs))

    def execute(self, *args, **kwargs) -> dict:
        """更新当前时间片 （time_slice）"""
        return {}

    def finialize(self):
        """结束 Actor 的执行。"""
        pass
