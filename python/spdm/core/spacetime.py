# -*- coding: utf-8 -*-
""" Space Volume """

from spdm.core.time import WithTime
from spdm.core.domain import WithDomain


class SpacetimeVolume(WithTime, WithDomain):
    """Spacetime Volume 是一个结合了空间和时间的概念，主要用于描述或分析在空间和时间上同时延展的现象或数据"""

    def __view__(self, **styles) -> dict:
        return styles
