import typing
import abc
from enum import Enum, auto, Flag

from .time import Time
from .entity import Entity
from .htree import List, Dict
from .edge import InPorts, OutPorts
from .sp_object import sp_object


@sp_object
class Event:
    """事件是某一时刻发生的独立、不可再分的操作或状态变化。
    事件是过程的组成部分。
    """

    timestamp: Time

    inports: InPorts

    outports: OutPorts

    @abc.abstractmethod
    def apply(self, time: Time = None):
        pass


class SpStage(Enum):
    """
    action on nodes
    NOTE (salmon 20200521): name of Stage should be a verb
    """

    null = 0
    initialize = auto()  # NOTE: auto( ) start at 1
    preprocess = auto()
    run = auto()
    postprocess = auto()
    finalize = auto()

    def next(self):
        return SpStage((self.value + 1) % (SpStage.finalize.value + 1))

    def prev(self):
        return SpStage((self.value - 1) % (SpStage.finalize.value + 1))


class SpState(Flag):
    """
    state of node
    NOTE (salmon 20200521): name of State should be an adjective
    """

    null = 0
    initialized = auto()  # turn on after initialize,     turn after before finalize
    active = auto()  # turn on after preprocess,     turn off after run
    executed = auto()  # turn on after run ,           turn off after postprocess
    valid = auto()  # turn on after postprocess,    turn off before preprocess

    looping = auto()
    break_point = auto()
    error = auto()
    pending = auto()  # True after pause,       False after resume,
    resuming = auto()  # True before resume,     False after resume,
