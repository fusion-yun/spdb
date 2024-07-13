import unittest

import numpy as np
from numpy.testing import assert_array_almost_equal
from scipy import constants
from spdm.core.expression import Expression, Variable
from spdm.numlib.calculus import derivative, antiderivative
from spdm.core.function import Function
from spdm.utils.logger import logger

TWOPI = constants.pi * 2.0


class TestFunction(unittest.TestCase):

    def test_delta_fun(self):
        p = 0.5
        value = 1.2345

        fun0 = Function(p, value)

        self.assertTrue(np.isclose(fun0(p), value))

        fun1 = Function([p], [value])

        self.assertTrue(np.isclose(fun1(p), value))

        x = np.linspace(0, 1, 11)

        mark = np.isclose(x, p)

        # logger.debug(fun1(x))
        self.assertTrue(np.allclose(fun1(x)[mark], value))
        self.assertTrue(np.all(np.isnan(fun1(x)[~mark])))

    def test_delta_nd(self):
        p = [0.5, 0.4]
        value = 1.2345

        fun0 = Function(*p, value)

        self.assertTrue(np.isclose(fun0(*p), value))

        dimx = np.linspace(0, 1, 11)
        dimy = np.linspace(0, 1, 11)

        x, y = np.meshgrid(dimx, dimy)

        mark = np.isclose(x, p[0]) & np.isclose(y, p[1])

        self.assertTrue(np.allclose(fun0(x, y)[mark], value))
        self.assertTrue(np.all(np.isnan(fun0(x, y)[~mark])))
