import typing
import unittest

import numpy as np
from scipy import constants
from spdm.utils.logger import logger
from spdm.core.geo_object import GeoObject


class TestMesh(unittest.TestCase):

    def test_line(self):
        p0 = (0, 0)
        p1 = (1, 1)
        gobj = GeoObject(p0, p1, type="line")
        self.assertEqual(type(gobj).__name__, "Line")
        from spdm.geometry.line import Line
        self.assertIsInstance(gobj, Line)

    def test_line2(self):
        from spdm.geometry.line import Line
        p0 = (4, 5, 6)
        p1 = (1, 2, 3)
        gobj = Line(p0, p1)

        self.assertEqual(type(gobj).__name__, "Line")
        self.assertTrue(np.all(np.isclose(gobj.p0[:], p0)))
        self.assertTrue(np.all(np.isclose(gobj.p1[:], p1)))

    def test_coordinates(self):
        from spdm.geometry.line import Line
        p0 = (4, 5, 6)
        p1 = (1, 2, 3)

        line = Line(p0, p1, coordinates="x,y,z")

        self.assertTrue(np.all(np.isclose(line.x, np.asarray([4, 1], dtype=float))))
        self.assertTrue(np.all(np.isclose(line.y, np.asarray([5, 2], dtype=float))))
        self.assertTrue(np.all(np.isclose(line.z, np.asarray([6, 3], dtype=float))))

    # def test_set(self):
    #     from spdm.geometry.Point import Point
    #     from spdm.geometry.GeoObject import GeoObjectSet
    #     gobj = GeoObjectSet(Point(1, 2, 3), Point(1, 2, 3))
    #     logger.debug(gobj.rank)
    #     logger.debug(len(gobj))


if __name__ == '__main__':
    unittest.main()
