import unittest

import numpy as np
from scipy import constants
from spdm.core.expression import Expression, Variable
from spdm.utils.logger import logger
from spdm.core.domain import Domain

TWOPI = constants.pi * 2.0


class TestDomain(unittest.TestCase):
    def test_define(self):

        _x = Variable(0, "x")
        _y = Variable(1, "y")

        d = Domain(_x > 0.3, _x < 0.7)

        self.assertTrue(d(0.5))
        self.assertFalse(d(0.3))

        x = np.linspace(0, 1, 10)
        y = np.zeros(10)

        y[d(x)] = 1
        y_ = np.asarray([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
        self.assertTrue(np.allclose(y, y_))

    def test_operation(self):

        _x = Variable(0, "x")

        d1 = Domain(_x > 0.3)
        d2 = Domain(_x < 0.7)

        d3 = ~(d1 & d2)

        x = np.linspace(0, 1, 10)
        y = np.zeros(10)

        y[d3(x)] = 1
        y_ = np.asarray([1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        self.assertTrue(np.allclose(y, y_))


if __name__ == "__main__":
    unittest.main()
