from __future__ import annotations

import abc
import os
import collections.abc
import datetime
import getpass

import matplotlib.pyplot as plt
import os

from ..utils.logger import logger
from ..core.sp_object import SpObject

SP_VIEW = os.environ.get("SP_VIEW", "matplotlib")

#  在 MatplotlibView 中 imported matplotlib 会不起作用
#  报错 : AttributeError: module 'matplotlib' has no attribute 'colors'. Did you mean: 'colormaps'?


class SpView(SpObject):
    """Abstract class for all views"""

    _plugin_singletons = {}
    _plugin_registry = {}
    _plugin_prefix = "spdm.view.view_"

    @property
    def signature(self) -> str:
        return f"Create by SpDM at {datetime.datetime.now().isoformat()}. AUTHOR: {getpass.getuser().capitalize()}. "

    @abc.abstractmethod
    def draw(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def plot(self, *args, **kwargs):
        pass


def display(*args, plugin=SP_VIEW, **kwargs):
    return SpView(_plugin_name=plugin).draw(*args, **kwargs)


def plot(*args, plugin=SP_VIEW, **kwargs):
    return SpView(_plugin_name=plugin).plot(*args, **kwargs)


from .render import Render

SP_RENDER = os.environ.get("SP_RENDER", "graphviz")


def render(*args, plugin=SP_RENDER, **kwargs):
    return Render(_plugin_name=plugin).apply(*args, **kwargs)
