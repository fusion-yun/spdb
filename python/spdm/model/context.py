import typing
import inspect
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_

from spdm.core.htree import HTree, List

from spdm.model.entity import Entity
from spdm.model.actor import Actor
from spdm.model.process import Process
from spdm.model.component import Component


class Context(Actor):
    """管理一组相互关联的 Actors，具有共同的时间 time 和 空间 Domain"""

    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return self

    def entities(self, type_hint=None) -> typing.Generator[typing.Tuple[str, Entity], None, None]:
        if type_hint is None:
            type_hint = Entity
        for k in getattr(self, "__properties__", []):
            entity = getattr(self, k, _not_found_)
            if isinstance(entity, type_hint):
                yield k, entity
            elif isinstance(entity, List) and isinstance(entity[0], type_hint):
                for i, a in enumerate(entity):
                    yield f"{k}_{i}", a

    def initialize(self, *args, **kwargs):
        for k, a in self.entities(Actor):
            logger.verbose(f"Initialize {k}")
            a.initialize(*args, **kwargs)

    def advance(self, *args, **kwargs):
        for _, a in self.entities(Actor):
            a.initialize(*args, **kwargs)

    def refresh(self, *args, **kwargs):
        for _, actor in self.entities(Actor):
            actor.refresh(*args, **kwargs)

    def flush(self):
        for _, a in self.entities(Actor):
            a.flush()

    def __getstate__(self) -> dict:
        return {k: v.__getstate__() for k, v in self.entities()}

    def __setstate__(self, state: typing.Dict) -> dict:
        for k, v in state.items():
            attr = getattr(self, k, _not_found_)
            if isinstance(attr, HTree):
                attr.__setstate__(v)

    def __view__(self, **styles) -> dict:
        geo = {"$styles": styles}

        # o_list = [
        #     "wall",
        #     "pf_active",
        #     "magnetics",
        #     "interferometer",
        #     "tf",
        #     "equilibrium",
        #     # "ec_launchers",
        #     # "ic_antennas",
        #     # "lh_antennas",
        #     # "nbi",
        #     # "pellets",
        # ]
        for k, g in self.entities((Component, Actor)):
            try:
                g_view = g.__view__(**styles)
            except RuntimeError as e:
                logger.error("Failed to get %s.__view__ ! ", g.__class__.__name__, exc_info=e)
                # raise RuntimeError(f"Can not get {g.__class__.__name__}.__view__ !") from error
            else:
                geo[k] = g_view

        view_point = (styles.get("view_point", None) or "rz").lower()

        if view_point == "rz":
            styles["xlabel"] = r"Major radius $R [m] $"
            styles["ylabel"] = r"Height $Z [m]$"

        styles.setdefault("title", self.title)

        return geo

    def __str__(self) -> str:
        actor_summary = "\n".join(f"{k:>19s} : {e.code} " for k, e in self.entities(Actor))
        processor_summary = "\n".join(f"{k:>19s} : {e.code} " for k, e in self.entities(Process))
        component_summary = ",".join(k for k, e in self.entities(Component))
        return f"""- Context           : {self.code} 
- Actors            :
{actor_summary}
- Processors        :
{processor_summary}
- Components        : {component_summary}
"""
