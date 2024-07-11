import unittest

import numpy as np
from numpy.testing import assert_array_almost_equal
from scipy import constants
from spdm.core.expression import Expression
from spdm.core.function import Function


TWOPI = constants.pi * 2.0


class TestFunction(unittest.TestCase):
    def test_np_fun(self):
        x = np.linspace(0, 1, 128)
        y = np.linspace(0, 2, 128)

        fun = Function(x, y)

        self.assertIsInstance(fun + 1, Expression)
        self.assertIsInstance(fun * 2, Expression)
        self.assertIsInstance(np.sin(fun), Expression)

    def test_operator(self):
        x = np.linspace(0, 1, 128)
        y = np.linspace(0, 2, 128)
        fun = Function(x, y)

        assert_array_almost_equal(-fun, -y)
        assert_array_almost_equal(fun + 2, y + 2)
        assert_array_almost_equal(fun - 2, y - 2)
        assert_array_almost_equal(fun * 2, y * 2)
        assert_array_almost_equal(fun / 2, y / 2)
        assert_array_almost_equal(fun**2, y**2)

    def test_interpolate(self):
        x = np.linspace(0, 1.0, 128)
        y = np.sin(x * TWOPI)

        fun = Function(x, y)

        assert_array_almost_equal(fun(x), y)


if __name__ == "__main__":
    unittest.main()
