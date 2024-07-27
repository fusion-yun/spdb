""" Context 
"""

import typing
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_

from spdm.core.htree import List, Set

from spdm.model.entity import Entity
from spdm.model.process import Process
from spdm.model.component import Component


class Context(Process):
    """管理一组相互关联的 Entities

    Attributes:
        context (typing.Self): 获取当前 Actor 所在的 Context。
    """

    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return self

    def entities(self, type_hint=None) -> typing.Generator[typing.Tuple[str, Entity], None, None]:
        """生成器函数，用于遍历 Context 中的 Entities。

        Args:
            type_hint (typing.Type[Entity], optional): 指定要遍历的 Entity 类型。默认为 None。

        Yields:
            typing.Tuple[str, Entity]: 包含 Entity 名称和 Entity 实例的元组。
        """
        if type_hint is None:
            type_hint = Entity
        for k in getattr(self, "__properties__", []):
            entity: Entity = getattr(self, k, _not_found_)  # type:ignore
            if isinstance(entity, type_hint):
                yield k, entity
            elif isinstance(entity, (List, Set)):
                for i, a in enumerate(entity):
                    if type_hint is None or isinstance(a, type_hint):
                        yield f"{k}[{i}]", a

    def processes(self) -> typing.Generator[typing.Tuple[str, Process], None, None]:
        """生成器函数，用于遍历 Context 中的 Process。

        Yields:
            typing.Tuple[str, Process]: 包含 Process 名称和 Process 实例的元组。
        """
        yield from self.entities(Process)  # type:ignore

    def components(self) -> typing.Generator[typing.Tuple[str, Component], None, None]:
        """生成器函数，用于遍历 Context 中的 Component。

        Yields:
            typing.Tuple[str, Component]: 包含 Component 名称和 Component 实例的元组。
        """
        yield from self.entities(Component)  # type:ignore

    def execute(self, *args, **kwargs) -> dict:
        """执行 Context"""

        return super().execute(*args, **kwargs) | {
            k: entity.execute(*args, **kwargs) for k, entity in self.processes()
        }

    def __view__(self, **styles) -> dict:
        """生成 Context 的视图。

        Args:
            **styles: 视图样式参数。

        Returns:
            dict: 包含 Context 视图的字典。
        """
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

        styles.setdefault("title", getattr(self, "title", None) or self._metadata.get("title", ""))

        return geo
