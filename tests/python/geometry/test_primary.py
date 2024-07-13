import typing
import unittest

import numpy as np
from numpy.testing import assert_array_equal

from spdm.utils.logger import logger
from spdm.core.geo_object import GeoObject


class TestGeometryObject(unittest.TestCase):

    def test_point(self):
        from spdm.geometry.point import Point

        p0: Point = GeoObject((0, 1, 2), kind="point")
        p1 = Point["xyz"](1, 2, 3)
        self.assertIsInstance(p0, Point)
        assert_array_equal(p0.points, np.asarray([0, 1, 2]))
        assert_array_equal(p1.points, np.asarray([1, 2, 3]))

        self.assertEqual(p1.x, 1)
        self.assertEqual(p1.y, 2)
        self.assertEqual(p1.z, 3)

    def test_line(self):

        from spdm.geometry.line import Line

        p0 = (0, 0)
        p1 = (1, 1)
        l0 = GeoObject(p0, p1, kind="line")
        l1 = Line["xy"]((p0, p1))
        self.assertIsInstance(l0, Line)
        assert_array_equal(l1.p0, np.asarray(p0))
        assert_array_equal(l1.p1, np.asarray(p1))
        assert_array_equal(l1.x, [p0[0], p1[0]])
        assert_array_equal(l1.y, [p0[1], p1[1]])

    # def test_set(self):
    #     from spdm.geometry.Point import Point
    #     from spdm.geometry.GeoObject import GeoObjectSet
    #     gobj = GeoObjectSet(Point(1, 2, 3), Point(1, 2, 3))
    #     logger.debug(gobj.rank)
    #     logger.debug(len(gobj))


if __name__ == "__main__":
    unittest.main()
