import unittest

import numpy as np
import scipy.constants
from spdm.core.expression import Expression, Piecewise, Variable
from spdm.utils.logger import logger

TWOPI = scipy.constants.pi * 2.0


class TestExpression(unittest.TestCase):
    def test_variable(self):
        _x = Variable(0, "x")
        _y = Variable(1, "y")

        self.assertEqual(_x.__label__, "x")
        self.assertEqual(str(_x + _y), "x + y")

    def test_expression(self):
        _x = Variable(0, "x")
        _y = Variable(1, "y")
        x = np.linspace(0.0, 1.0, 10)
        y = np.linspace(1.0, 2.0, 10)
        expr = np.sqrt(_x / _y)
        self.assertEqual(expr(1, 2), np.sqrt(0.5))
        self.assertTrue(np.allclose(expr(x, y), np.sqrt(x / y)))

    def test_picewise(self):
        _x = Variable(0)

        r_ped = 0.90  # np.sqrt(0.88)
        Cped = 0.2
        Ccore = 0.4
        chi = Piecewise([_x * 2 * Ccore, Cped], [_x < r_ped, _x >= r_ped])
        self.assertEqual(chi(0.5), (0.5 * 2 * Ccore))
        self.assertEqual(chi(0.95), Cped)

        x = np.linspace(0, 1, 101)

        res = (chi**2)(x)

        self.assertTrue(np.allclose(res[x < r_ped], (x[x < r_ped] * 2 * Ccore) ** 2))
        self.assertTrue(np.allclose(res[x >= r_ped], (Cped) ** 2))

    def test_constant_fun(self):
        value = 1.2345
        xmin = 0.0
        xmax = 1.0
        ymin = 2.0
        ymax = 3.0

        dims_a = np.linspace(xmin, xmax, 5), np.linspace(ymin, ymax, 5)

        fun1 = Function(value)

        xa, ya = np.meshgrid(*dims_a)

        self.assertTrue(np.allclose(fun1(xa, ya), value))

        fun2 = Function(value, *dims_a)

        dims_b = np.linspace(xmin - 0.5, xmax + 0.5, 10), np.linspace(ymin - 0.5, ymax + 0.5, 10)

        xb, yb = np.meshgrid(*dims_b)
        marker = (xb >= xmin) & (xb <= xmax) & (yb >= ymin) & (yb <= ymax)

        e_a = np.full_like(xa, value, dtype=float)

        e_b = np.full_like(xb, value, dtype=float)

        e_b[~marker] = np.nan

        self.assertTrue(np.allclose(fun2(xa, ya), e_a))

        self.assertTrue(np.allclose(fun2(xb, yb), e_b, equal_nan=True))

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


if __name__ == "__main__":
    unittest.main()
