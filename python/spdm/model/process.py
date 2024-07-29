""" Process module"""

import typing
import abc
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.core.sp_tree import SpProperty, SpTree
from spdm.core.htree import Set
from spdm.core.sp_tree import annotation
from spdm.model.port import Ports


class Process(abc.ABC):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._in_ports_hash = 0

        self._in_ports = self.InPorts(_parent=self)
        self._out_ports = self.OutPorts(_parent=self)

    @property
    def in_ports(self) -> InPorts:
        return self._in_ports

    @property
    def out_ports(self) -> typing.Self | OutPorts:
        return self._out_ports

    def __hash__(self) -> int:
        return hash(tuple([super().__hash__(), self._in_ports_hash]))

    def refresh(self, *args, **kwargs) -> OutPorts:
        """刷新 Processor 的状态，将执行结果更新的out_ports"""

        kwargs = self.in_ports.push(*args, **kwargs)

        if len(kwargs) > 0:
            logger.debug(f"{self}: Ignore inputs {[*kwargs.keys()]}")

        in_ports_hash = self.in_ports.validate()

        if in_ports_hash != self._in_ports_hash:
            # 只有在 input hash 改变时才执行 execute。
            res = self.execute(**self.in_ports.pull())
            self.out_ports.__setstate__(res)
            self._in_ports_hash = in_ports_hash

        return self.out_ports

    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> typing.Any:
        """执行 Processor 的操作，返回结果"""
        logger.debug("Execute: %s", str(self))
        return {}


_T = typing.TypeVar("_T", bound=Process)


class ProcessBundle(Process, Set[_T]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._in_ports = self._parent.in_ports
        self._out_ports = self

    def execute(self, *args, **kwargs):
        return [process.execute(*args, **kwargs) for process in self]

    # @sp_property
    # def name(self) -> str:
    #     return "[" + " , ".join(p.name for p in self) + "]"

    def __str__(self) -> str:
        return "[" + " , ".join(str(p) for p in self if isinstance(p, Process)) + "]"

    def __view__(self, *args, **kwargs) -> dict:
        return {}
