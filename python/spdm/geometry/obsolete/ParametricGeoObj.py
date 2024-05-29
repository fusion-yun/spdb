
import collections.abc
import typing
from functools import cached_property

import numpy as np

from ..utils.logger import logger
from ..utils.misc import builtin_types
from ..utils.plugin import Pluggable
from ..utils.typing import (ArrayLike, ArrayType, NumericType, ScalarType,
                            nTupleType, numeric_type)
from .geo_object import GeoObject


class ParametricGeoObj(GeoObject):
    """
        参数化几何对象（Parametric geometry object）是指使用参数方程来定义的几何对象。
        参数方程是一种数学方法，它定义了一组量作为一个或多个独立变量（称为参数）的函数1。
        参数方程通常用于表示构成几何对象（如曲线或曲面）的点的坐标，分别称为参数曲线和参数曲面1。
    """
    def remesh(self, *args, **kwargs): raise NotImplementedError(f"")

    def coordinates(self, *uvw) -> NumericType:
        """
            将 _参数坐标_ 转换为 _空间坐标_
            @return: array-like shape = [*uvw.shape[:-1],ndim]
        """
        raise NotImplementedError(f"{self.__class__.__name__}")

    def parametric_coordinates(self, *xyz) -> NumericType:
        """
            将 _空间坐标_ 转换为 _参数坐标_         
            @return: array-like shape = [*uvw.shape[:-1],rank]
        """
        raise NotImplementedError(f"{self.__class__.__name__}.parametric_coordinates")

    def xyz(self, *uvw) -> NumericType: return self.coordinates(*uvw)
    """ alias of coordinates """

    def uvw(self, *xyz) -> NumericType: return self.parametric_coordinates(*xyz)
    """ alias of parametric_coordinates """

    def dl(self, uv=None) -> NumericType: return np.asarray(0)
    """
        derivative of shape
        Returns:
            rank==0 : 0
            rank==1 : dl (shape=[n-1])
            rank==2 : dx (shape=[n-1,m-1]), dy (shape=[n-1,m-1])
            rank==3 : dx (shape=[n-1,m-1,l-1]), dy (shape=[n-1,m-1,l-1]), dz (shape=[n-1,m-1,l-1])
    """

    def integral(self, func: typing.Callable) -> ScalarType: raise NotImplementedError(f"")

    def average(self, func: typing.Callable) -> ScalarType: return self.integral(func)/self.measure

    def derivative(self,  *args, **kwargs): return NotImplemented

    def pullback(self, func,   *args, **kwargs):
        r"""
            ..math:: f:N\rightarrow M\\\Phi^{*}f:\mathbb{R}\rightarrow M\\\left(\Phi^{*}f\right)\left(u\right)&\equiv f\left(\Phi\left(u\right)\right)=f\left(r\left(u\right),z\left(u\right)\right)
        """

        return NotImplemented
