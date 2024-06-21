import unittest

import numpy as np
from scipy import constants
from spdm.core.expression import Expression, Variable, derivative, antiderivative
from spdm.core.function import Function
from spdm.utils.logger import logger

TWOPI = constants.pi * 2.0


class TestFunction(unittest.TestCase):
    def test_expression(self):
        x = np.linspace(0, 1.0, 128)
        y = np.sin(x * TWOPI)

        fun = Function(x, y)
        expr = fun * 2.0
        self.assertTrue(type(expr) is Expression)

    def test_operator(self):
        x = np.linspace(0, 1, 128)
        y = np.linspace(0, 2, 128)
        fun = Function(x, y)

        self.assertTrue(np.all(-fun == -y))
        self.assertTrue(np.all(fun + 2 == y + 2))
        self.assertTrue(np.all(fun - 2 == y - 2))
        self.assertTrue(np.all(fun * 2 == y * 2))
        self.assertTrue(np.all(fun / 2 == y / 2))
        self.assertTrue(np.all(fun**2 == y**2))
        # self.assertTrue(np.all(fun @ fun == y)

    def test_construct_from_expression(self):
        x = np.linspace(0, 1, 128)
        y = np.linspace(0, 2, 128)
        
        fun = Function(x, y * 2)

        self.assertTrue(np.allclose(fun, y * 2))

    def test_np_fun(self):
        x = np.linspace(0, 1, 128)
        y = np.linspace(0, 2, 128)

        fun = Function(x, y)

        self.assertTrue(type(fun + 1) is Expression)
        self.assertTrue(type(fun * 2) is Expression)
        self.assertTrue(type(np.sin(fun)) is Expression)

    def test_spl(self):
        x = np.linspace(0, 1.0, 128)
        y = np.sin(x * TWOPI)

        fun = Function(x, y)

        x2 = np.linspace(0, 1.0, 64)

        y2 = np.sin(x2 * TWOPI)

        self.assertTrue(np.allclose(y2, fun(x2)))

    def test_antiderivative(self):
        _x = Variable(0, "x")
        sinx = derivative(np.sin(_x), _x)
        cosx = np.cos(_x)

        x = np.linspace(0, TWOPI, 128)
        self.assertTrue(np.allclose(sinx(x), cosx(x)))


if __name__ == "__main__":
    unittest.main()
