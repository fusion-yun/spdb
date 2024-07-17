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

    in_ports: Ports
    out_ports: Ports

    def execute(self):
        pass
