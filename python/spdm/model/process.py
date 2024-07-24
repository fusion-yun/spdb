""" Process module"""

import typing

from spdm.utils.tags import _not_found_
from spdm.core.htree import Set
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
        self.in_ports.connect(self.context, **kwargs)
        self.out_ports.connect(self.context, **kwargs)
        super().__setstate__(*args)

    def refresh(self, *args, **kwargs) -> typing.Self | Ports:
        self.in_ports.push(*args, **kwargs)
        return self.out_ports

    def finialize(self):
        self.in_ports.clear()
        self.out_ports.clear()

    def __call__(self, *args, **kwargs) -> typing.Self | dict:
        res = self.refresh(*args, **kwargs)
        if isinstance(res, Ports):
            return res.pull()
        else:
            return res


_T = typing.TypeVar("_T", bound=Process)


class ProcessBundle(Set[_T], Process):

    def initialize(self, *args, **kwargs):
        super().initialize(getattr(self._parent, "in_ports", _not_found_), *args, **kwargs)
        for process in self:
            process.initialize(self.in_ports)

    def refresh(self, *args, **kwargs) -> typing.Self | Ports:
        res = super().refresh(getattr(self._parent, "in_ports", _not_found_), *args, **kwargs)
        for process in self:
            process.refresh(self.in_ports)
        return res

    def finialize(self):
        for process in self:
            process.finialize()
