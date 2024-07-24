"""This module defines the `Port`, `Ports`, `InPorts`, `OutPorts`, and `Edge` classes.

 The `Port` class represents a connection point in a graph. It contains information about the source node,
 the fragment path, the type hint, and metadata.

The `Ports` class is a collection of `Port` objects. It provides methods for putting and getting values from the ports.


"""

import typing
from spdm.utils.tags import _not_found_
from spdm.core.path import Path
from spdm.core.htree import HTreeNode
from spdm.core.sp_tree import SpTree
from spdm.core.sp_tree import AttributeTree
from spdm.core.generic import Generic

from spdm.model.entity import Entity

_T = typing.TypeVar("T")


class Port(Generic[_T], SpTree):
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

    def __init__(self, name, node=None, fragment=None, type_hint=None, **kwargs):
        super().__init__(
            {
                "name": name,
                "node": node,
                "fragment": fragment,
                "type_hint": type_hint,
                **kwargs,
            }
        )

    node: HTreeNode

    type_hint: typing.Type

    name: str

    path: Path

    fragment: Path | set | str

    metadata: AttributeTree

    @property
    def valid(self) -> bool:
        return self.node is not None and self.node is not _not_found_

    def connect(self, node):
        """Binds the port to a node."""
        self.node = node

    def get(self, default_value=_not_found_) -> _T:
        """Fetches data from the port."""

        if len(self.fragment) > 0:
            return Path().find(self.node, self.fragment)
        else:
            return self.node

    def put(self, value):
        """Fetches data from the port."""
        return self.fragment.put(self.node, value)


class Ports(SpTree):
    """A collection of ports.

    Args:
        typing (_type_): _description_
    """

    def push(self, *args, **kwargs):
        for a in (*args, kwargs):
            self._cache = Path().update(self._cache, a)
        ctx = getattr(self._parent, "context", None)
        if ctx is not None:
            for k in self.__properties__:
                if self._cache.get(k, _not_found_) is not _not_found_:
                    self._cache[k] = getattr(ctx, k, _not_found_)

    def pull(self) -> dict:
        return {k: self._cache[k] for k in self.__properties__ if k in self._cache}

    def connect(self, *args, **kwargs):
        self.push(*args, **kwargs)

    def disconnect(self):
        if self._cache is _not_found_:
            return

        for k in self.__properties__:
            del self._cache[k]
