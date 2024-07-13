import typing
import inspect
from spdm.model.actor import Actor
from spdm.model.time_sequence import TimeSlice


class Context(Actor[TimeSlice]):
    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return self

    @property
    def actors(self) -> typing.Generator[Actor, None, None]:
        # for member in inspect.get_members(self):
        #     if isinstance(member, Actor):
        #         yield member
        return

    def initialize(self, *args, **kwargs) -> None:

        super().initialize(*args, **kwargs)

        for actor in self.actors:
            actor.in_ports.connect(self)

        self.out_ports.connect(self)
