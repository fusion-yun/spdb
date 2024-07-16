import typing
import inspect
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.core.htree import HTree
from spdm.core.time import WithTime
from spdm.core.domain import WithDomain
from spdm.model.actor import Actor
from spdm.model.component import Component


class Context(WithTime, Actor):
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
        for k in getattr(self, "__properties__", []):
            obj = getattr(self, k, _not_found_)
            if isinstance(obj, (Actor)):
                yield k, obj

    def components(self) -> typing.Generator[Component, None, None]:
        for k in getattr(self, "__properties__", []):
            obj = getattr(self, k, _not_found_)
            if isinstance(obj, Component):
                yield k, obj

    def initialize(self, *args, **kwargs):
        for k, a in self.actors():
            logger.verbose(f"Initialize {k}")
            a.initialize(*args, **kwargs)

    def advance(self, *args, **kwargs):
        for a in self.actors():
            a.initialize(*args, **kwargs)

    def refresh(self, *args, **kwargs):
        super().refresh(*args, **kwargs)
        for actor in self.actors():
            actor.refresh(*args, **kwargs)

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
        for o_name in getattr(self, "__properties__", []):
            g = getattr(self, o_name, _not_found_)
            if isinstance(g, (Component, Actor)):
                if hasattr(g.__class__, "__view__"):
                    try:
                        g_view = g.__view__(**styles)
                    except RuntimeError as e:
                        logger.error("Failed to get %s.__view__ ! ", g.__class__.__name__, exc_info=e)
                        # raise RuntimeError(f"Can not get {g.__class__.__name__}.__view__ !") from error
                    else:
                        geo[o_name] = g_view

        view_point = (styles.get("view_point", None) or "rz").lower()

        if view_point == "rz":
            styles["xlabel"] = r"Major radius $R [m] $"
            styles["ylabel"] = r"Height $Z [m]$"

        styles.setdefault("title", self.title)

        return geo
