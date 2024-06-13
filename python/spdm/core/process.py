import typing

from .event import Event
from .sp_object import sp_object


@sp_object
class Process:
    """描述实体状态随时间变化的过程，如运动、传热等。过程描述了一个连续的活动序列，
    这些活动会导致实体状态的改变。过程通常是由一系列事件组成的。
    """

    events: typing.List[Event]
