import typing
import inspect
from spdm.utils.tags import _not_found_
from spdm.core.htree import HTree
from spdm.core.time import WithTime
from spdm.core.domain import WithDomain
from spdm.model.actor import Actor


class Context(WithTime, WithDomain, Actor):
    """管理一组相互关联的 Actors，具有共同的时间 time 和 空间 Domain"""

    def __getstate__(self) -> dict:
        return {k: v.__getstate__() for k, v in inspect.getmembers(self) if isinstance(v, HTree)}

    def __setstate__(self, state: typing.Dict) -> dict:
        for k, v in state.items():
            attr = getattr(self, k, _not_found_)
            if isinstance(attr, HTree):
                attr.__setstate__(v)

    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return self

    def actors(self) -> typing.Generator[Actor, None, None]:
        for member in inspect.get_members(self):
            if isinstance(member, Actor):
                yield member

    def initialize(self, *args, **kwargs):
        for a in self.actors():
            a.initialize(*args, **kwargs)

    def advance(self, *args, **kwargs):
        for a in self.actors():
            a.initialize(*args, **kwargs)

    def refresh(self, *args, **kwargs):
        super().refresh(*args, **kwargs)
        for actor in self.actors():
            actor.refresh(*args, **kwargs)
