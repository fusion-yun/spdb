from __future__ import annotations

import abc
import os
import datetime
import getpass

import matplotlib.pyplot as plt
import os

from spdm.utils.logger import logger
from spdm.core.pluggable import Pluggable

SP_VIEW = os.environ.get("SP_VIEW", "matplotlib")

#  在 MatplotlibView 中 imported matplotlib 会不起作用
#  报错 : AttributeError: module 'matplotlib' has no attribute 'colors'. Did you mean: 'colormaps'?


class _JupyterView:
    """用以在 JupyterLab 中显示图形"""

    def __init__(self, svg):
        self._svg = svg

    def _repr_svg_(self) -> str:
        return self._svg


class SpView(Pluggable, plugin_prefix="spdm/view/view_"):
    """Abstract class for all views"""

    _plugin_registry = {}

    DEFAULT_VIEWPOINT = "RZ"

    @property
    def signature(self) -> str:
        return f"Create by SpDM at {datetime.datetime.now().isoformat()}. AUTHOR: {getpass.getuser().capitalize()}. "

    @abc.abstractmethod
    def draw(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def plot(self, *args, **kwargs):
        pass


def draw(*args, output=None, **kwargs):
    """
    Usage:
        output=None, inplace, <output path>.png....
        默认
    """

    fig = SpView(_plugin_name=SP_VIEW).draw(*args, output=output, **kwargs)

    if output is None and isinstance(fig, str):
        return _JupyterView(fig)
    else:
        return fig


def plot(*args, output=None, **kwargs):
    fig = SpView(_plugin_name=SP_VIEW).plot(*args, output=output, **kwargs)

    if output is None and isinstance(fig, str):
        return _JupyterView(fig)
    else:
        return fig


def display(*args, **kwargs):
    return draw(*args, **kwargs)


from spdm.view.render import Render

SP_RENDER = os.environ.get("SP_RENDER", "graphviz")


def render(*args, plugin=SP_RENDER, **kwargs):
    return Render(type=plugin).apply(*args, **kwargs)
