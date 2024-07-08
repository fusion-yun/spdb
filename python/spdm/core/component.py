import typing

from spdm.core.entity import Entity
from spdm.core.signal import Signal
from spdm.core.geo_object import GeoObject


class Component(Entity):
    """Component（组件）用于描述系统中的独立单元或部件，
        这些部件可以被组合在一起形成更复杂的系统。

    - 组件是一个独立的、可替换和可组合的单元，具有明确的接口和行为。
    - 组件可以包含数据、功能或者二者的组合，并通过接口与其他组件进行通信。
    - 组件是一个聚合，其中的实体各自独立随时间演化（Signal）
    """

    _DEFAULT_TYPE_HINT = Signal

    def time_slice(self, time=None) -> typing.Self:
        """返回当前时间点的状态树"""
        raise NotImplementedError("TODO: time_slice ")

    @property
    def geometry(self) -> GeoObject:
        return {}
