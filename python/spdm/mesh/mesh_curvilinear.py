from __future__ import annotations

import typing
import numpy as np
from scipy import interpolate
from functools import cached_property

from spdm.utils.type_hint import ArrayType
from spdm.core.geo_object import GeoObject
from spdm.geometry.point import Point


from spdm.mesh.mesh_rectilinear import RectilinearMesh


class CurvilinearMesh(RectilinearMesh, plugin_name="curvilinear"):
    """A `curvilinear Mesh` or `structured Mesh` is a Mesh with the same combinatorial structure as a regular Mesh,
    in which the cells are quadrilaterals or [general] cuboids, rather than rectangles or rectangular cuboids.
    -- [https://en.wikipedia.org/wiki/Regular_Mesh]
    """

    TOLERANCE = 1.0e-5

    def axis(self, idx, axis=0):
        if axis == 0:
            return self.geometry[idx]
        else:
            s = [slice(None, None, None)] * self.geometry.ndims
            s[axis] = idx
            s = s + [slice(None, None, None)]

            sub_xy = self.xy[tuple(s)]  # [p[tuple(s)] for p in self._xy]
            sub_uv = [self._uv[(axis + i) % self.geometry.ndim] for i in range(1, self.geometry.ndim)]
            sub_cycles = [self.cycles[(axis + i) % self.geometry.ndim] for i in range(1, self.geometry.ndim)]

            return CurvilinearMesh(sub_xy, sub_uv, cycles=sub_cycles)

    @property
    def uv(self) -> ArrayType:
        return self._uv

    @property
    def points(self) -> ArrayType:
        if not isinstance(self.geometry, GeoObject):
            raise RuntimeError(f"Unknown type {type(self.geometry)}")
        return self.geometry.points

    @cached_property
    def volume_element(self) -> ArrayType:
        raise NotImplementedError()

    def interpolator(self, value, **kwargs):
        if value.shape != self.shape:
            raise ValueError(f"{value.shape} {self.shape}")

        if self.ndims == 1:
            interp = interpolate.InterpolatedUnivariateSpline(self.dims[0], value, **kwargs)
        elif self.ndims == 2:
            interp = interpolate.RectBivariateSpline(self.dims[0], self.dims[1], value, **kwargs)
        else:
            raise NotImplementedError(f"NDIMS {self.ndims}>2")
        return interp

    @cached_property
    def boundary(self):
        return {"inner": self.axis(0, 0), "outer": self.axis(-1, 0)}

    @cached_property
    def geo_object(self):
        if self.rank == 1:
            if all([np.var(x) / np.mean(x**2) < CurvilinearMesh.TOLERANCE for x in self.xy.T]):
                gobj = Point(*[x[0] for x in self.xy.T])
            else:
                gobj = CubicSplineCurve(self.xy, self._uv[0], is_closed=self.cycles[0])
        elif self.rank == 2:
            gobj = BSplineSurface(self.xy, self._uv, is_closed=self.cycles)
        else:
            raise NotImplementedError()

        return gobj
