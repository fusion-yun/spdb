"""
This module provides a base class for creating objects from a registry.

Classes:
- Pluggable: Factory class to create objects from a registry.
"""

import abc
import typing
from importlib import resources as impresources
import importlib
import importlib.util
import sys

from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger


def walk_namespace_modules(namespace: str, ignores: str | typing.List[str] = "__pycache__:obsolete"):
    """
    Walks a namespace and returns a list of all modules found within it.
    This function is useful for discovering all modules within a package.
    :param namespace: The namespace to walk.
    :param ignores: A list of directories to ignore.
    """
    if isinstance(ignores, str):
        ignores = ignores.split(":")

    namespace = namespace.strip(".")

    if "__init__.py" in impresources.contents(namespace):
        yield namespace
    else:
        for sub in impresources.contents(namespace):
            if sub in ignores:
                continue
            elif sub.endswith(".py"):
                yield namespace + "." + sub[:-3]
            else:
                yield from walk_namespace_modules(namespace + "." + sub, ignores=ignores)


def sp_load_module(mod_path: str | typing.List[str]):

    if not isinstance(mod_path, list):
        mod_path = mod_path.split(":")

    module = None

    for m_name in mod_path:
        module = sys.modules.get(m_name, None)  # if module is loaded, use it

        if module is not None:
            break

        try:
            spec = importlib.util.find_spec(m_name)
        except ModuleNotFoundError:
            continue

        if spec is not None:
            module = importlib.util.module_from_spec(spec)

            spec.loader.exec_module(module)

            sys.modules[spec.name] = module

            logger.verbose(f"Load module {spec.name}")  # from {pathlib.Path(spec.origin).resolve().as_posix()}

            break

    return module


class Pluggable(abc.ABC):
    """
    Factory class to create objects from a registry.

    Attributes:
    - _plugin_registry: A dictionary to store the registered plugins.
    """

    _plugin_registry = {}

    @classmethod
    def _complete_path(cls, plugin_name: str) -> str:
        """
        Return the complete name of the plugin.

        Args:
        - plugin_name: The name of the plugin.

        Returns:
        - str | None: The complete name of the plugin, or None if the plugin name is invalid.
        """

        if not isinstance(plugin_name, str):
            raise TypeError(f"Illegal plugin name {plugin_name}!")

        plugin_name = plugin_name.lower().replace("+", "_")

        if not plugin_name.isidentifier():
            raise RuntimeError(f"Illegal plugin name {plugin_name}!")

        prefix = getattr(cls, "_plugin_prefix", None)

        if prefix is None:
            prefix = cls.__module__ + "."

        prefix = prefix.replace("/", ".").lstrip(".")

        if not plugin_name.startswith(prefix):
            plugin_name = prefix + f"{plugin_name}"

        return plugin_name

    @classmethod
    def register(cls, plugin_name: str | list | None = None, plugin_cls=None):
        """
        Decorator to register a class to the registry.

        Args:
        - plugin_name: The name of the plugin.
        - plugin_cls: The class to be registered as a plugin.
        """
        if plugin_cls is not None and plugin_name is not None:
            if not isinstance(plugin_name, list):
                plugin_name = [plugin_name]

            for name in plugin_name:
                if not isinstance(name, str):
                    continue
                p_name = cls._complete_path(name)
                if not hasattr(plugin_cls, "__plugin_name__"):
                    plugin_cls.__plugin_name__ = p_name

                cls._plugin_registry[p_name] = plugin_cls

            return None

        def decorator(o_cls):
            cls.register(plugin_name, o_cls)
            return o_cls

        return decorator

    @classmethod
    def _get_plugin(cls, plugin_name: str) -> type:
        """
        Find a plugin by name.

        Args:
        - plugin_name: The name of the plugin.

        Returns:
        - typing.Type[typing.Self]: The plugin class.
        """
        if plugin_name is None:
            plugin_name = getattr(cls, "_plugin_default", None)

        if plugin_name is None:
            return cls

        # Check if the plugin path is provided
        plugin_name = cls._complete_path(plugin_name)

        # Check if the plugin is already registered
        n_cls = cls._plugin_registry.get(plugin_name, None)

        if n_cls is None:
            # Plugin not found in the registry
            # Try to find the module in PYTHON_PATH and register it to _plugin_registry
            sp_load_module(plugin_name)

            # Recheck
            n_cls = cls._plugin_registry.get(plugin_name, None)

        if n_cls is None:
            raise RuntimeError(f"Can not find module '{plugin_name}' as subclass of '{cls.__name__}'! ")

        return n_cls

    @classmethod
    def _all_plugins(cls) -> typing.Generator[str, None, None]:
        """
        Find all plugins in the Python path.F

        Yields:
        - str: The names of the plugins.
        """
        yield from cls._plugin_registry.keys()
        for p in walk_namespace_modules(cls._complete_path("")):
            if p not in cls._plugin_registry:
                yield p

    def __new__(cls, *args, _plugin_name=None, **kwargs) -> typing.Self:
        """Create a new instance of the class."""

        if "_plugin_prefix" not in cls.__dict__ and _plugin_name is None:
            return object.__new__(cls)

        if cls is Pluggable:
            # Can not create instance of Pluggable
            raise RuntimeError("Can not create instance of Pluggable!")

        if not issubclass(cls, Pluggable):
            # Not pluggable
            raise RuntimeError(f"{cls.__name__} is not pluggable!")

        n_cls = cls._get_plugin(_plugin_name)

        # Return the plugin class
        return object.__new__(n_cls)

    def __init_subclass__(
        cls, plugin_name: str | list = None, plugin_default=None, plugin_prefix=None, **kwargs
    ) -> None:
        if plugin_default is not None:
            cls._plugin_default = plugin_default

        if plugin_prefix is not None:
            if not plugin_prefix.startswith("/"):
                plugin_prefix = f"{getattr(cls,'_plugin_prefix','')}{plugin_prefix}".replace(".", "/")
            cls._plugin_prefix = plugin_prefix

        if plugin_name is not None and plugin_name is not _not_found_:
            cls._plugin_name = plugin_name
            cls.register(plugin_name, cls)

        super().__init_subclass__(**kwargs)
