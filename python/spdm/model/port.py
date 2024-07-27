"""This module defines the `Port`, `Ports`, `InPorts`, `OutPorts`, and `Edge` classes.

 The `Port` class represents a connection point in a graph. It contains information about the source node,
 the fragment path, the type hint, and metadata.

The `Ports` class is a collection of `Port` objects. It provides methods for putting and getting values from the ports.


"""

import typing
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger
from spdm.core.path import Path
from spdm.core.htree import HTreeNode
from spdm.core.sp_tree import SpTree


class Ports(SpTree):
    """A collection of ports."""

    def push(self, state: dict = None, **kwargs) -> None:
        if isinstance(state, dict):
            kwargs = state | kwargs
        elif state is not None:
            logger.debug(f"Ignore {state}")

        for k, v in kwargs.items():
            if k in self.__properties__:
                obj = Path([k]).get(self._cache, _not_found_)
                if isinstance(obj, HTreeNode) and not isinstance(v, HTreeNode):
                    obj.__setstate__(v)
                else:
                    self._cache = Path([k]).update(k, v)

    def pull(self) -> dict:
        return {k: self.get(k, _not_found_) for k in self.__properties__}

    def connect(self, ctx=None, **kwargs) -> None:
        if ctx is not None:
            self.connect(
                **({k: getattr(ctx, k, _not_found_) for k in self.__properties__ if k not in kwargs} | kwargs)
            )
        else:
            self.push(**kwargs)

    def disconnect(self, name: str = None) -> None:
        if self._cache is _not_found_:
            pass
        elif name is None:
            for k in self.__properties__:
                del self._cache[k]
        elif name in self._cache:
            del self._cache[name]
