"""This module defines the Event class and related enums for the SpDM framework."""

import typing
from enum import Enum, auto, Flag

from spdm.core.time import Time
from spdm.core.port import Ports
from spdm.core.sp_object import sp_object, SpObject


@sp_object
class Event(SpObject):
    """An Event represents an independent and indivisible operation or state change that occurs at a specific moment in time.
    Events are the building blocks of processes.

    Attributes:
        timestamp (Time): The timestamp of the event.
        inports (InPorts): The input ports associated with the event.
        outports (OutPorts): The output ports associated with the event.
    """

    timestamp: Time

    inports: Ports

    outports: Ports

    def apply(self):
        """Applies the event."""


class InputEvent(Event):
    """Represents an input event."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__([args, kwargs])


class OutputEvent(Event):
    """Represents an output event."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__([args, kwargs])


def as_event(obj) -> typing.Type[Event]:
    """
    Converts the given object to an instance of the Event class if it is not already an instance.

    Parameters:
        obj: Any object that needs to be converted to an Event instance.

    Returns:
        An instance of the Event class.

    """
    return obj if isinstance(obj, Event) else Event(obj)


class SpStage(Enum):
    """
    Represents the stages of an action on nodes.
    NOTE (salmon 20200521): The name of a stage should be a verb.
    """

    null = 0
    initialize = auto()  # NOTE: auto( ) starts at 1
    preprocess = auto()
    run = auto()
    postprocess = auto()
    finalize = auto()

    def next(self):
        """Returns the next stage in the sequence."""
        return SpStage((self.value + 1) % (SpStage.finalize.value + 1))

    def prev(self):
        """Returns the previous stage in the sequence."""
        return SpStage((self.value - 1) % (SpStage.finalize.value + 1))


class SpState(Flag):
    """
    Represents the states of a node.
    NOTE (salmon 20200521): The name of a state should be an adjective.
    """

    null = 0
    initialized = auto()  # Turned on after initialize, turned off before finalize
    active = auto()  # Turned on after preprocess, turned off after run
    executed = auto()  # Turned on after run, turned off after postprocess
    valid = auto()  # Turned on after postprocess, turned off before preprocess

    looping = auto()
    break_point = auto()
    error = auto()
    pending = auto()  # True after pause, False after resume
    resuming = auto()  # True before resume, False after resume
