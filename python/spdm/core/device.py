from __future__ import annotations

from ..utils.logger import logger
from ..utils.envs import SP_DEBUG, SP_LABEL
from ..utils.plugin import Pluggable
from ..view import View as sp_view

from .signal import Signal
from .htree import HTreeNode
from .sp_object import SpObject


class Device(SpObject):
    """描述一个现实对象的状态历史，其属性随时间变化的属性具有 Signal类型

    Args:
        Pluggable (_type_): _description_
        SpTree (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
