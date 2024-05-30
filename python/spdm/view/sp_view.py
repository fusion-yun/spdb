from __future__ import annotations
from ..utils.plugin import Pluggable
from ..utils.logger import logger, SP_DEBUG

import collections
import collections.abc
import datetime
import getpass
import typing

import matplotlib.pyplot as plt
import os


#  在 MatplotlibView 中 imported matplotlib 会不起作用
#  报错 : AttributeError: module 'matplotlib' has no attribute 'colors'. Did you mean: 'colormaps'?


class SpView(Pluggable):
    """Abstract class for all views"""

    _plugin_registry = {}
    _plugin_prefix = "spdm.view.view_"

    backend = None

    # @classmethod
    # def __dispatch_init__(cls, _backend_type, self, *args, **kwargs) -> None:

    #     if isinstance(_backend_type, str):
    #         _backend_type = [_backend_type,
    #                          f"spdm.view.{_backend_type}#{_backend_type}",
    #                          f"spdm.view.{_backend_type}{cls.__name__}#{_backend_type}{cls.__name__}",
    #                          f"spdm.view.{_backend_type.capitalize()}#{_backend_type.capitalize()}",
    #                          f"spdm.view.{_backend_type.capitalize()}{cls.__name__}#{_backend_type.capitalize()}{cls.__name__}",
    #                          f"spdm.view.{cls.__name__}#{_backend_type}"
    #                          f"spdm.plugins.view.{_backend_type}#{_backend_type}",
    #                          f"spdm.plugins.view.{_backend_type}{cls.__name__}#{_backend_type}{cls.__name__}",
    #                          f"spdm.plugins.view.{_backend_type.capitalize()}#{_backend_type.capitalize()}",
    #                          f"spdm.plugins.view.{_backend_type.capitalize()}{cls.__name__}#{_backend_type.capitalize()}{cls.__name__}",
    #                          f"spdm.plugins.view.{cls.__name__}#{_backend_type}"
    #                          ]

    #     super().__dispatch_init__(_backend_type, self, *args, **kwargs)

    def __init__(self, *args, **kwargs) -> None:
        if self.__class__ is SpView:
            SpView.__dispatch_init__(kwargs.pop("backend", None), self, *args, **kwargs)
            return

    @property
    def signature(self) -> str:
        return f"Create by SpDM at {datetime.datetime.now().isoformat()}. AUTHOR: {getpass.getuser().capitalize()}. "

    def draw(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__}.display")

    def plot(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__}.draw")


_view_instances = {}


def viewer(backend=None):
    """Get a viewer instance"""

    if backend is None:
        backend = SP_VIEW_BACKEND  # "matplotlib"

    instance = _view_instances.get(backend, None)

    if instance is None:
        instance = _view_instances[backend] = SpView(backend=backend)

    return instance


SP_VIEW_BACKEND = "matplotlib"


def display(*args,   backend=None,  **kwargs):
    """Show an object"""

    return viewer(backend).draw(*args,  **kwargs)


def plot(*args,   backend=None, **kwargs):
    """Show an object"""
    return viewer(backend=backend).plot(*args,  **kwargs)
