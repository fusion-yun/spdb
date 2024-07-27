""" Process module"""

import typing
import abc
from spdm.utils.tags import _not_found_
from spdm.utils.misc import try_hash
from spdm.core.htree import Set
from spdm.core.sp_tree import sp_property, annotation
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inputs_hash = 0

    class InPorts(Ports, final=False):
        """输入端口集合。"""

    class OutPorts(Ports, final=False):
        """输出端口集合。"""

    in_ports: InPorts

    out_ports: OutPorts

    def __hash__(self) -> int:
        return hash(tuple([super().__hash__(), self._inputs_hash]))

    def check_inputs(self, *args, **kwargs):
        if len(kwargs) == 0:
            kwargs = self.in_ports.pull()
        elif self.in_ports is not _not_found_ and len(self.in_ports) > 0:
            kwargs = self.in_ports.pull() | kwargs

        return args, kwargs, hash(tuple([try_hash(args), try_hash(kwargs)]))

    def refresh(self, *args, **kwargs) -> None:
        """刷新 Processor 的状态，将执行结果更新的out_ports"""
        args, kwargs, input_hash = self.check_inputs(*args, **kwargs)
        if input_hash != self._inputs_hash:
            # 只有在 input hash 改变时才执行 execute。
            self._inputs_hash = input_hash
            self.out_ports.push(self.execute(*args, **kwargs))

    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> dict | list:
        """执行 Processor 的操作，返回结果"""
        pass


_T = typing.TypeVar("_T", bound=Process)


class ProcessBundle(Set[_T], Process):

    def __init__(self, cache: list | tuple | set = None, **kwargs):
        Set.__init__(self, cache)
        Process.__init__(self, **kwargs)

        #
        # TODO:
        # - 汇总输出

        self.out_ports = self

    in_ports: Process.InPorts = annotation(alias=".../in_ports")

    def execute(self, *args, **kwargs) -> typing.List[typing.Any]:
        return [process.execute(*args, **kwargs) for process in self]

    @sp_property
    def name(self) -> str:
        return "[" + " , ".join(p.name for p in self) + "]"

    def __str__(self) -> str:
        return "[" + " , ".join(p.name for p in self) + "]"
