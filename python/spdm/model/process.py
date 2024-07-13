"""Defines the Process class that represents a change of entity state over time."""

import abc

from spdm.core.graph import MultiDiGraph
from spdm.core.time import Time
from spdm.core.sp_tree import sp_tree

from spdm.model.event import Event, InputEvent, OutputEvent
from spdm.model.port import Port, Ports


class Process(MultiDiGraph[Port | Event], Event):
    """
    Describes a process that represents the change of entity state over time, such as motion, heat transfer, etc.
    A process describes a continuous sequence of activities that result in changes to the entity's state.
    Processes are typically composed of a series of events.
    """

    def __init__(self, *args, **kwargs) -> None:
        MultiDiGraph[Port | Event].__init__(*args, **kwargs)
        Event.__init__(self)

    input: InputEvent
    output: OutputEvent

    def inports(self) -> Ports:
        """
        Returns the input ports of the process.

        Returns:
            Dict[str, Port]: The input ports of the process.
        """
        return self.inputs.inports

    def outports(self) -> Ports:
        """
        Returns the output ports of the process.

        Returns:
            Dict[str, Port]: The output ports of the process.
        """
        return self.outputs.outports

    @abc.abstractmethod
    def apply(self, time: Time = None):
        """Applies the event.

        Args:
            time (Time, optional): The time at which the event is applied. Defaults to None.
        """
