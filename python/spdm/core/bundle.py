from __future__ import annotations

from ..utils.logger import logger
from .sp_object import SpObject


class Bundle(SpObject):
    """同类 Actor 的合集

    Args:
        Pluggable (_type_): _description_
        SpTree (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
