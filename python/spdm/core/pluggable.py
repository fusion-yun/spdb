import abc
import collections
import collections.abc
import inspect
from enum import Enum
import typing

from abc import ABC, abstractmethod

from ..utils.logger import logger
from ..utils.sp_export import sp_find_module, sp_load_module, walk_namespace_modules
from ..utils.tags import _not_found_


class Pluggable(ABC):
    """Factory class to create objects from a registry."""

    _plugin_registry = {}

    @classmethod
    def _plugin_complete_path(cls, plugin_name=None, *args, **kwargs) -> str:

        path: str | list = getattr(cls, "_plugin_prefix", None)

        if path is None:
            path = cls.__module__.split(".")

            path = path[0:1] + ["plugins"] + path[1:]
            # if path[-1] != cls.__name__:
            #     path += [cls.__name__]
        else:
            path = path.split(".")

        if isinstance(plugin_name, str):
            path.append(plugin_name)
        elif isinstance(plugin_name, list):
            path.extend(plugin_name)

        return ".".join(path)

    @classmethod
    def register(cls, plugin_name: str | list | None = None, plugin_cls=None):
        """
        Decorator to register a class to the registry.
        """
        if plugin_cls is not None:
            if not isinstance(plugin_name, list):
                plugin_name = [plugin_name]

            for name in plugin_name:
                if not isinstance(name, str):
                    continue
                cls._plugin_registry[cls._plugin_complete_path(name)] = plugin_cls

        else:

            def decorator(o_cls):
                cls.register(plugin_name, o_cls)
                return o_cls

            return decorator

    @classmethod
    def _find_plugins(cls) -> typing.Generator[None, None, str]:
        """Find all plugins in the Python path."""
        yield from cls._plugin_registry.keys()
        for p in walk_namespace_modules(cls._plugin_complete_path()):
            if p not in cls._plugin_registry:
                yield p

    def __new__(cls, *args, **kwargs) -> typing.Type[typing.Self]:
        if not issubclass(cls, Pluggable):
            logger.error(f"{cls.__name__} is not pluggable!")
            raise RuntimeError(f"{cls.__name__} is not pluggable!")

        elif len(cls.__abstractmethods__) == 0:
            return super(Pluggable, cls).__new__(cls)

        else:

            plugin_path = cls._plugin_complete_path(*args, **kwargs)

            n_cls = cls._plugin_registry.get(plugin_path, None)

            if n_cls is None:
                
                # 尝试从 PYTHON_PATH 中查找 module, 并 load 

                sp_load_module(plugin_path)

                n_cls = cls._plugin_registry.get(plugin_path, None)

            if not (inspect.isclass(n_cls) and issubclass(n_cls, cls)):
                raise ModuleNotFoundError(
                    f"Can not find module as subclass of '{cls.__name__}'  {plugin_path} in {cls._plugin_registry}!"
                )

            return super(Pluggable, cls).__new__(n_cls)

    @abstractmethod
    def _plugin_path(self) -> str:
        pass
