import abc
import collections
import collections.abc
import inspect
import os
import sys
from enum import Enum
import typing

from .logger import logger
from .misc import camel_to_snake
from .sp_export import sp_find_module, sp_load_module, walk_namespace_modules
from .tags import _not_found_


class Pluggable(metaclass=abc.ABCMeta):
    """Factory class to create objects from a registry."""

    _plugin_prefix = None
    _plugin_registry = {}

    @classmethod
    def _get_plugin_fullname(cls, name: str) -> str:
        prefix = getattr(cls, "_plugin_prefix", None)
        if prefix is None:
            name = name.replace("/", ".").lower()
            m_pth = camel_to_snake(cls.__module__).split(".")
            prefix = ".".join(m_pth[0:1] + ["plugins"] + m_pth[1:] + [""]).lower()
            cls._plugin_prefix = prefix
        if not name.startswith(prefix):
            name = prefix + name
        return name

    @classmethod
    def register(cls, sub_list: str | list | None = None, plugin_cls=None):
        """
        Decorator to register a class to the registry.
        """
        if plugin_cls is not None:
            if not isinstance(sub_list, list):
                sub_list = [sub_list]

            for name in sub_list:
                if not isinstance(name, str):
                    continue
                cls._plugin_registry[cls._get_plugin_fullname(name)] = plugin_cls

            return plugin_cls
        else:

            def decorator(o_cls):
                cls.register(sub_list, o_cls)
                return o_cls

            return decorator

    @classmethod
    def plugin_tag(cls) -> str:
        return f"{cls._plugin_prefix}{cls.__name__.lower()}"

    @classmethod
    def _plugin_guess_name(cls, self, *args, **kwargs) -> str | None:
        return kwargs.pop("plugin_name", None)

    @classmethod
    def __dispatch_init__(cls, sub_list, self, *args, **kwargs) -> None:
        if sub_list is None:
            sub_list = cls._plugin_guess_name(self, *args, **kwargs)

        if sub_list is None:
            sub_list = []
        elif not isinstance(sub_list, list):
            sub_list = [sub_list]

        n_cls = None

        for sub_cls in sub_list:
            if sub_cls is None or sub_cls is _not_found_ or sub_cls == "":
                continue

            if isinstance(sub_cls, Enum):
                sub_cls = sub_cls.name

            if inspect.isclass(sub_cls):
                n_cls = sub_cls
                sub_cls = n_cls.__name__
            elif not isinstance(sub_cls, str):
                logger.warning(f"Invalid plugin name {sub_cls}!")
                continue
            elif sub_cls == "dummy":
                n_cls = cls
                break
            else:
                cls_name = cls._get_plugin_fullname(sub_cls)

                if cls_name not in cls._plugin_registry:
                    sp_load_module(cls_name)

                n_cls = cls._plugin_registry.get(cls_name, None)

            if n_cls is not None:
                break

        if (n_cls is cls or n_cls is None) and ("dummy" in sub_list or len(sub_list) == 0):
            return
        elif inspect.isclass(n_cls) and issubclass(n_cls, cls):
            self.__class__ = n_cls
            n_cls.__init__(self, *args, **kwargs)

        else:
            raise ModuleNotFoundError(
                f"Can not find module as subclass of '{cls.__name__}' {n_cls} from {sub_list} in {cls._plugin_registry}!"
            )

    def __init__(self, *args, **kwargs) -> None:
        if self.__class__ is Pluggable:
            self.__class__.__dispatch_init__(None, self, *args, **kwargs)
            return

    @classmethod
    def _find_plugins(cls) -> typing.List[str]:
        """Find all plugins in the Python path.

        仅返回可的module （import 成功的）
        """
        head = len(cls._plugin_prefix)
        return [p[head:] for p in walk_namespace_modules(cls._plugin_prefix[:-1])]
