"""This module defines the `Port`, `Ports`, `InPorts`, `OutPorts`, and `Edge` classes.

The `Port` class represents a connection point in a graph. It contains information about the source node, the fragment path, the type hint, and metadata.

The `Ports` class is a collection of `Port` objects. It provides methods for putting and getting values from the ports.


"""

from __future__ import annotations
import typing
from spdm.core.path import Path, as_path
from spdm.core.htree import HTreeNode


class Port:
    """
    Represents a port in a graph edge.

    Args:
        source (HTreeNode): The source node of the port.
        fragment (Path | str, optional): The fragment path or string. Defaults to None.
        type_hint (typing.Type, optional): The type hint for the port. Defaults to None.
        **kwargs: Additional metadata for the port.

    Attributes:
        node (HTreeNode): The source node of the port.
        type_hint (typing.Type): The type hint for the port.
        fragment (Path): The fragment path of the port.
        metadata (typing.Dict): Additional metadata for the port.

    Methods:
        update: Updates the port with new values.
        link: Creates an edge between the current port and a target port.
        fetch: Fetches data from the port.
        is_changed: Checks if the port has changed.

    """

    def __init__(
        self,
        source: HTreeNode = None,
        fragment: Path | str = None,
        type_hint: typing.Type = None,
        **kwargs,
    ) -> None:
        self._node = source
        self._fragment: Path = as_path(fragment)
        self._type_hint: typing.Type = type_hint
        self._metadata = kwargs

    @property
    def node(self) -> HTreeNode:
        """
        Returns the HTreeNode object associated with this edge.

        Returns:
            HTreeNode: The HTreeNode object associated with this edge.
        """
        return self._node

    @property
    def type_hint(self) -> typing.Type:
        """
        Returns the type hint for the port.

        Returns:
            typing.Type: The type hint for the port.
        """
        return self._type_hint

    @property
    def fragment(self) -> Path:
        """
        Returns the fragment path of the port.

        Returns:
            Path: The fragment path of the port.
        """
        return self._fragment

    @property
    def metadata(self) -> typing.Dict:
        """Returns the additional metadata for the port."""
        return self._metadata

    def bind(self, node):
        """Binds the port to a node."""
        self._node = node

    def fetch(self):
        """Fetches data from the port."""
        value = self.fragment.get(self._node, None)
        # TODO: type/value convert
        return value


class Ports:
    """A collection of ports.

    Args:
        typing (_type_): _description_
    """

    def __init__(self, *args, **kwargs) -> None:
        self._args = list(args)
        self._kwargs = dict(kwargs)

    def put(self, path, value, *args, **kwargs):
        return as_path(path).update(self._cache, value, *args, **kwargs)

    def get(self, path, *args, **kwargs) -> Port | None:
        """
        Retrieves the port at the specified path.

        Args:
            path: The path to the port.
            **kwargs: Additional keyword arguments.

        Returns:
            The port at the specified path, or None if not found.
        """
        pth = as_path(path)
        match len(pth):
            case 0:
                return Port()
            case 1:
                return self._cache.get(pth[0], **kwargs)
            case _:
                return pth.get(self._cache, **kwargs)

    def __missing__(self, key: str | int) -> typing.Any:
        raise KeyError(f"{self.__class__.__name__}.{key} is not assigned! ")
