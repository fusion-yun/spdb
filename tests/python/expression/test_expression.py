import unittest

import numpy as np
from numpy.testing import assert_array_almost_equal
import scipy.constants
from spdm.core.expression import Variable, Expression, Scalar

TWOPI = scipy.constants.pi * 2.0


class TestExpression(unittest.TestCase):
    def test_variable(self):
        _x = Variable(0, "x")
        _y = Variable(1, "y")
        expr = _x + _y

        self.assertEqual(str(_x), "x")

        self.assertIsInstance(expr, Expression)

        self.assertEqual(str(expr), "{x} + {y}")

    def test_expression(self):
        _x = Variable(0, "x")
        _y = Variable(1, "y")

        expr = np.sqrt(_x / _y)
        res = expr(1.0, 2.0)
        self.assertIsInstance(res, float)
        self.assertEqual(res, np.sqrt(0.5))

        x = np.random.random(10)
        y = np.random.random(10)
        assert_array_almost_equal(expr(x, y), np.sqrt(x / y))

    def test_constant(self):
        value = 1.2345
        xmin = 0.0
        xmax = 1.0
        ymin = 2.0
        ymax = 3.0

        dims_a = np.linspace(xmin, xmax, 5), np.linspace(ymin, ymax, 5)

        fun1 = Scalar(value)

        xa, ya = np.meshgrid(*dims_a)

        assert_array_almost_equal(fun1(xa, ya), value)

    # def test_mark(self):
    #     value = 1.2345
    #     xmin = 0.0
    #     xmax = 1.0
    #     ymin = 2.0
    #     ymax = 3.0

    #     dims_a = np.linspace(xmin, xmax, 5), np.linspace(ymin, ymax, 5)

    #     xa, ya = np.meshgrid(*dims_a)

    #     fun2 = Scalar(*dims_a, value)

    #     dims_b = np.linspace(xmin - 0.5, xmax + 0.5, 10), np.linspace(ymin - 0.5, ymax + 0.5, 10)

    #     xb, yb = np.meshgrid(*dims_b)

    #     marker = (xb >= xmin) & (xb <= xmax) & (yb >= ymin) & (yb <= ymax)

    #     e_a = np.full_like(xa, value, dtype=float)

    #     e_b = np.full_like(xb, value, dtype=float)

    #     e_b[~marker] = np.nan

    #     assert_array_almost_equal(fun2(xa, ya), e_a)

    #     assert_array_almost_equal(fun2(xb, yb), e_b)

    # def test_picewise(self):
    #     _x = Variable(0)
    #     r_ped = 0.90  # np.sqrt(0.88)
    #     Cped = 0.2
    #     Ccore = 0.4
    #     chi = Piecewise([_x * 2 * Ccore, Cped], [_x < r_ped, _x >= r_ped])
    #     self.assertEqual(chi(0.5), (0.5 * 2 * Ccore))
    #     self.assertEqual(chi(0.95), Cped)

    #     x = np.linspace(0, 1, 101)

    #     res = (chi**2)(x)

    #     self.assertTrue(np.allclose(res[x < r_ped], (x[x < r_ped] * 2 * Ccore) ** 2))
    #     self.assertTrue(np.allclose(res[x >= r_ped], (Cped) ** 2))


if __name__ == "__main__":
    unittest.main()
