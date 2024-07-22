import typing
import inspect
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_

from spdm.core.htree import HTree, List, Set

from spdm.model.entity import Entity
from spdm.model.actor import Actor
from spdm.model.process import Process
from spdm.model.component import Component


class Context(Actor):
    """管理一组相互关联的 Entities"""

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
            elif isinstance(entity, (List, Set)):
                for i, a in enumerate(entity):
                    if type_hint is None or isinstance(a, type_hint):
                        yield f"{k}[{i}]", a

    def initialize(self):
        """初始化 Context
        - 初始化 Actor 和 Process
        - 构建 DAG 执行图
        """
        # for k, a in self.entities(Actor):
        #     logger.verbose(f"Initialize {k}")
        #     a.initialize()

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
            else:
                setattr(self, k, v)

    def __view__(self, **styles) -> dict:
        geo = {"$styles": styles}

        for k, g in self.entities():
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
