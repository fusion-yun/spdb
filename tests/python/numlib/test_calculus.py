import unittest

import numpy as np
from scipy import constants
from numpy.testing import assert_array_almost_equal

from spdm.utils.logger import logger

from spdm.core.expression import Variable
from spdm.core.function import Function
from spdm.numlib.calculus import antiderivative, derivative, partial_derivative

TWOPI = constants.pi * 2.0


class TestCalculus(unittest.TestCase):

    def test_dydx(self):

        _x = Variable(0, "x")

        x = np.linspace(0, TWOPI, 512)

        Y = Function(np.sin(_x), x, periods=[TWOPI])

        assert_array_almost_equal(np.sin(x), Y(x), decimal=4)

        dY = derivative(Y)(x)

        assert_array_almost_equal(np.cos(x), dY, rtol=1.0e-4)

        # logger.debug((-(TWOPI**2)*np.sin(x))[:10])
        # logger.debug(Y.d(2)(x)[:10])
        # assert_array_almost_equal(-(TWOPI**2)*np.sin(x), Y.d(2)(x), rtol=0.10))

    def test_integral(self):

        x = np.linspace(0, TWOPI, 512)

        _x = Variable(0, "x")

        Y = Function(np.cos(_x), x, periods=[TWOPI])

        Y1 = antiderivative(Y)

        assert_array_almost_equal(np.sin(x), Y1(x), decimal=4)

    def test_spl2d(self):

        x = np.linspace(0, TWOPI, 128)
        y = np.linspace(0, 2 * TWOPI, 128)
        g_x, g_y = np.meshgrid(x, y)

        z = np.sin(g_x) * np.cos(g_y)

        _x = Variable(0, "x")

        _y = Variable(1, "y")

        fun = Function(np.sin(_x) * np.cos(_y), x, y, periods=[TWOPI, 2 * TWOPI])

        z2 = fun(g_x, g_y)

        assert_array_almost_equal(z, z2, decimal=4)

    def test_pd2(self):

        x = np.linspace(0, TWOPI, 128)
        y = np.linspace(0, 2 * TWOPI, 128)

        g_x, g_y = np.meshgrid(x, y)

        _x = Variable(0, "x")
        _y = Variable(1, "y")

        Z = Function(np.sin(_x) * np.cos(_y), x, y, periods=[TWOPI, 2 * TWOPI])

        assert_array_almost_equal(np.sin(g_x) * np.cos(g_y), Z(g_x, g_y), decimal=4)

        dZdx = partial_derivative(Z, 1, 0)
        assert_array_almost_equal(np.cos(g_x) * np.cos(g_y), dZdx(g_x, g_y), decimal=4)

        # ignore boundary points
        assert_array_almost_equal(
            (-np.sin(g_x) * np.sin(g_y))[2:-2, 2:-2], Z.pd(0, 1)(g_x, g_y)[2:-2, 2:-2], decimal=4
        )


if __name__ == "__main__":
    unittest.main()
