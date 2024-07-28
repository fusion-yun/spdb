"""This module defines the `Port`, `Ports`, `InPorts`, `OutPorts`, and `Edge` classes.

 The `Port` class represents a connection point in a graph. It contains information about the source node,
 the fragment path, the type hint, and metadata.

The `Ports` class is a collection of `Port` objects. It provides methods for putting and getting values from the ports.


"""

import typing
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger
from spdm.utils.misc import try_hash

from spdm.core.path import Path
from spdm.core.htree import HTreeNode
from spdm.core.sp_tree import SpTree


class Ports(SpTree):
    """A collection of ports."""

    def __init__(self, *args, _entry=None, **kwargs):
        # Ports 不接受 entry 参数。
        super().__init__(*args, **kwargs)

    def push(self, state: dict = None, **kwargs) -> None:
        if isinstance(state, dict):
            kwargs = state | kwargs
        elif state is not None:
            logger.debug(f"Ignore {state}")

        for k in self.__properties__:
            v = kwargs.pop(k, _not_found_)
            if v is _not_found_:
                continue
            obj = Path([k]).get(self._cache, _not_found_)
            if isinstance(obj, HTreeNode) and not isinstance(v, HTreeNode):
                obj.__setstate__(v)
            else:
                self._cache = Path([k]).update(self._cache, v)
        return kwargs

    def pull(self) -> dict:
        return {k: self.get(k) for k in self.__properties__ if self._cache is not _not_found_ and k in self._cache}

    def connect(self, ctx=None, **kwargs) -> None:
        if ctx is not None:
            self.push({k: getattr(ctx, k, _not_found_) for k in self.__properties__ if k not in kwargs}, **kwargs)
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

    def validate(self) -> int:
        inports = {}
        missing = []
        for k in self.__properties__:
            obj = self.get(k, _not_found_)
            if obj is not _not_found_:
                inports[k] = obj
            else:
                missing.append(k)

        if len(missing) > 0:
            raise RuntimeError(f"{self._parent.__class__.__name__} missing arguments: {missing}")
        else:
            return try_hash(inports)
