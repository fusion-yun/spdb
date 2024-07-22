"""
Processor: 处理或转换数据的组件。
"""

from spdm.model.port import Ports
from spdm.model.entity import Entity


class Process(Entity):
    """Processor: 处理或转换数据的组件。
    - 一个 Processor 可以有多个输入端口和多个输出端口。
    - Processor 是无状态的，即不会保存任何状态信息。
    - Processor 可以是同步的，也可以是异步的。
    - Processor 可以是有向无环图（DAG）的节点。
    - Processor 可以是一个单元操作，也可以是一个复合操作。
    - Processor 可以是一个数据处理流程的一部分。

    """

    class InPorts(Ports, final=False):
        """输入端口集合。"""

    class OutPorts(Ports, final=False):
        """输出端口集合。"""

    in_ports: InPorts
    out_ports: OutPorts

    def initialize(self, *args, **kwargs):
        self.in_ports.connect(self.context)
        self.out_ports.connect(self.context)
        super().__setstate__(*args, **kwargs)

    def execute(self) -> dict:
        return {}

    def finialize(self):
        self.in_ports.disconnect()
        self.out_ports.disconnect()

    def __call__(self, *args, **kwargs) -> dict:
        self.in_ports.pull(*args, **kwargs)
        res = self.execute()
        self.out_ports.push(res)
        return self.out_ports.__getstate__()
