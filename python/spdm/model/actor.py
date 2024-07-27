""" Actor """

from spdm.model.process import Process


class Actor(Process):
    """执行体，具有状态历史和空间区域的实体。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_ports = self
