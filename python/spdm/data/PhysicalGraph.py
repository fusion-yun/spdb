import functools

import numpy as np

from ..util.LazyProxy import LazyProxy
from .Coordinates import Coordinates
from .Graph import Graph
from .Node import _last_, _next_
from .Quantity import Quantity


class PhysicalGraph(Graph):
    r"""
       "PhysicalGraph" is a set of "quantities" (nodes) with internal mutual constraints (edges).

    """

    def __init__(self, *args, coordinates=None, **kwargs) -> None:
        if coordinates is not None:
            coordinates = coordinates if isinstance(coordinates, Coordinates) else Coordinates(coordinates)

        if coordinates is not None:
            self._coordinates = coordinates

        super().__init__(*args, coordinates=coordinates, **kwargs)
        self._changed = True

    @property
    def coordinates(self):
        return getattr(self, "_coordinates", None) or getattr(self._value, "coordinates", None) or getattr(self._parent, "coordinates", None)

    @property
    def __changed__(self):
        return self._changed

    def __update__(self, *args, **kwargs):
        super().__update__(*args, **kwargs)
        self._changed = True

    def __new_node__(self, *args, parent=None, **kwargs):
        return PhysicalGraph(*args,  parent=parent or self, **kwargs)

    def __getattr__(self, k):
        if k.startswith("_"):
            return super().__getattr__(k)
        else:
            res = getattr(self.__class__, k, None)
            if res is None:
                res = self.__getitem__(k)
            elif isinstance(res, property):
                res = getattr(res, "fget")(self)
            elif isinstance(res, functools.cached_property):
                res = res.__get__(self)
            return res

    def __setattr__(self, k, v):
        if k.startswith("_"):
            super().__setattr__(k, v)
        else:
            res = getattr(self.__class__, k, None)
            if res is None:
                self.__setitem__(k, v)
            elif isinstance(res, property):
                res.fset(self, k, v)
            else:
                raise AttributeError(f"Can not set attribute {k}!")

    def __delattr__(self, k):
        if k.startswith("_"):
            super().__delattr__(k)
        else:
            res = getattr(self.__class__, k, None)
            if res is None:
                self.__delitem__(k)
            elif isinstance(res, property):
                res.fdel(self, k)
            else:
                raise AttributeError(f"Can not delete attribute {k}!")

    def __pre_process__(self, value, *args, coordinates=None, **kwargs):
        # if not isinstance(value, (Quantity, collections.abc.Mapping, collections.abc.Sequence)) or isinstance(value, str):
        if isinstance(value, np.ndarray) and not isinstance(value, Quantity):
            value = Quantity(value, *args, coordinates=coordinates or self.coordinates, **kwargs)
        return value

    def __postprocess__(self, value, *args, **kwargs):
        return super().__post_process__(value, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        value = self.__value__
        if callable(value):
            return value(*args, **kwargs)
        else:
            return value