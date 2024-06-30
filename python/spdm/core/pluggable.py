"""
This module provides a base class for creating objects from a registry.

Classes:
- Pluggable: Factory class to create objects from a registry.
"""

import inspect
import typing
import abc  # Abstract Base Classes

from spdm.utils.sp_export import sp_load_module, walk_namespace_modules
from spdm.utils.logger import logger


class Pluggable(abc.ABC):
    """
    Factory class to create objects from a registry.

    Attributes:
    - _plugin_registry: A dictionary to store the registered plugins.
    """

    _PLUGIN_TAGS = ("plugin_name",)

    _plugin_registry = {}

    _plugin_name = None

    @classmethod
    def _complete_path(cls, plugin_name) -> str | None:
        """
        Return the complete name of the plugin.

        Args:
        - plugin_name: The name of the plugin.

        Returns:
        - str | None: The complete name of the plugin, or None if the plugin name is invalid.
        """

        if not isinstance(plugin_name, str):
            raise TypeError(f"Illegal plugin name {plugin_name}!")

        plugin_name = plugin_name.replace("+", "_")

        if not plugin_name.isidentifier():
            raise RuntimeError(f"Illegal plugin name {plugin_name}!")

        prefix = getattr(cls, "_plugin_prefix", None)

        if prefix is None:
            prefix = cls.__module__ + "."

        return prefix + f"{plugin_name}"

    @classmethod
    def register(cls, plugin_name: str | list | None = None, plugin_cls=None):
        """
        Decorator to register a class to the registry.

        Args:
        - plugin_name: The name of the plugin.
        - plugin_cls: The class to be registered as a plugin.
        """
        if plugin_cls is not None:
            if not isinstance(plugin_name, list):
                plugin_name = [plugin_name]

            for name in plugin_name:
                if not isinstance(name, str):
                    continue
                cls._plugin_registry[cls._complete_path(name)] = plugin_cls

            return None

        def decorator(o_cls):
            cls.register(plugin_name, o_cls)
            return o_cls

        return decorator

    @classmethod
    def _find_plugin(cls, plugin_name: str) -> typing.Self:
        """
        Find a plugin by name.

        Args:
        - plugin_name: The name of the plugin.

        Returns:
        - typing.Type[typing.Self]: The plugin class.
        """
        # Check if the plugin path is provided
        plugin_path = cls._complete_path(plugin_name)

        if plugin_path is None or plugin_path == cls.__module__ or plugin_path == getattr(cls, "_plugin_prefix", None):
            # No plugin path provided, return the class itself
            n_cls = None
        else:
            # Check if the plugin is already registered
            n_cls = cls._plugin_registry.get(plugin_path, None)

            if n_cls is None:
                # Plugin not found in the registry
                # Try to find the module in PYTHON_PATH and register it to _plugin_registry

                if sp_load_module(plugin_path) is None:
                    s_path = plugin_path.split(".")
                    s_path = s_path[0:1] + ["plugins"] + s_path[1:]
                    sp_load_module(".".join(s_path))

                # Recheck
                n_cls = cls._plugin_registry.get(plugin_path, None)

        return n_cls

    def __new__(cls, *args, _plugin_name=None, **kwargs):
        """
        Create a new instance of the class.

        Args:
        - args: Positional arguments.
        - kwargs: Keyword arguments.

        Returns:
        - typing.Type[typing.Self]: The new instance of the class.
        """

        if cls is Pluggable:
            # Can not create instance of Pluggable
            raise RuntimeError("Can not create instance of Pluggable!")

        if not issubclass(cls, Pluggable):
            # Not pluggable
            logger.error("%s is not pluggable!", cls.__name__)
            raise RuntimeError(f"{cls.__name__} is not pluggable!")

        if _plugin_name is None:
            n_cls = cls
        else:

            n_cls = cls._find_plugin(_plugin_name)

            if not (inspect.isclass(n_cls) and issubclass(n_cls, cls)):
                raise ModuleNotFoundError(f"Can not find module '{_plugin_name}' as subclass of '{cls.__name__}'! ")

        instance = object.__new__(n_cls)

        # Return the plugin class
        return instance

    def __init_subclass__(cls, *args, plugin_name=None, **kwargs) -> None:

        if plugin_name is not None:
            cls.register(plugin_name, cls)
        return super().__init_subclass__()

    @classmethod
    def _find_plugins(cls) -> typing.Generator[None, None, str]:
        """
        Find all plugins in the Python path.F

        Yields:
        - str: The names of the plugins.
        """
        yield from cls._plugin_registry.keys()
        for p in walk_namespace_modules(cls._complete_path("")):
            if p not in cls._plugin_registry:
                yield p
