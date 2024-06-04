import unittest

import numpy as np
import scipy.constants

from spdm.core.expression import Variable
from spdm.core.field import Field
from spdm.utils.logger import logger

TWOPI = scipy.constants.pi * 2.0


class TestField(unittest.TestCase):
    def test_attribute(self):
        x = np.linspace(0, 1 * TWOPI, 128)
        y = np.linspace(0, 2 * TWOPI, 128)

        _x = Variable(0, "x")
        _y = Variable(1, "y")
        fun = Field(x, y, np.sin(_x) * np.cos(_y), mesh={"periods": [TWOPI, 2 * TWOPI]})

        self.assertEqual(fun.mesh.ndim, 2)
        self.assertTrue(np.allclose(fun.mesh.dims[0], x))
        self.assertTrue(np.allclose(fun.mesh.dims[1], y))

    def test_spl2d(self):
        _x = Variable(0, "x")
        _y = Variable(1, "y")
        x = np.linspace(0, 1 * TWOPI, 128)
        y = np.linspace(0, 2 * TWOPI, 128)
        g_x, g_y = np.meshgrid(x, y)

        z = np.sin(g_x) * np.cos(g_y)

        fun = Field(x, y, np.sin(_x) * np.cos(_y), mesh={"periods": [TWOPI, 2 * TWOPI]})

        z2 = fun(g_x, g_y)

        self.assertTrue(np.allclose(z, z2, rtol=1.0e-4))

    def test_pd(self):
        _x = Variable(0, "x")
        _y = Variable(1, "y")
        x = np.linspace(0, TWOPI, 128)
        y = np.linspace(0, 2 * TWOPI, 128)
        g_x, g_y = np.meshgrid(x, y)

        Z = Field(x, y, np.sin(_x) * np.cos(_y), mesh={"periods": [TWOPI, 2 * TWOPI]})

        self.assertTrue(np.allclose(np.sin(g_x) * np.cos(g_y), Z(g_x, g_y), rtol=1.0e-4))

        self.assertTrue(np.allclose(np.cos(g_x) * np.cos(g_y), Z.pd(1, 0)(g_x, g_y), rtol=1.0e-4))

        # dzdx = TWOPI*np.cos(g_x*TWOPI)*np.cos(g_y*TWOPI)
        # dZdx = Z.pd(1, 0)(g_x, g_y)
        # # logger.debug(np.count_nonzero(~np.isclose(dzdx, dZdx, rtol=1.0e-4)))
        # self.assertTrue(np.allclose(dzdx, dZdx, rtol=1.0e-4))

        # dzdy = -TWOPI*np.sin(g_x*TWOPI)*np.sin(g_y*TWOPI)
        # dZdy = Z.pd(0, 1)(g_x, g_y)
        # logger.debug(np.count_nonzero(~np.isclose(dzdy, dZdy, rtol=1.0e-4)))
        # self.assertTrue(np.allclose(dzdy, dZdy, rtol=1.0e-4))

        # dZdxdy = Z.pd(1, 1)(g_x, g_y)
        # dzdxdy = -(TWOPI)*(TWOPI)*np.cos(g_x*TWOPI)*np.sin(g_y*TWOPI)
        # logger.debug(np.count_nonzero(~np.isclose(dzdxdy, dZdxdy, rtol=1.0e-4)))
        # self.assertTrue(np.allclose(dzdxdy, dZdxdy, rtol=1.0e-4))


if __name__ == "__main__":
    unittest.main()
