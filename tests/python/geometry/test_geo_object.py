import unittest

from numpy.testing import assert_array_equal


from spdm.core.geo_object import GeoObject


class TestGeoObject(unittest.TestCase):

    def test_define_new_class(self):

        class GObj(GeoObject, ndim=2, rank=1, plugin_name="gobj"):
            pass

        obj = GObj(10, 10)
        print(obj._metadata)
        self.assertEqual(obj.ndim, 2)
        self.assertEqual(obj.rank, 1)

    def test_classgetitem(self):
        class Point(GeoObject, rank=0):
            pass

        Point2DRZ = Point["RZ", 2]

        p = Point2DRZ(10, 12)
        self.assertEqual(Point2DRZ.__name__, "PointRZ2D")
        self.assertEqual(p.ndim, 2)
        self.assertEqual(p.rank, 0)
        self.assertEqual(p.r, 10)
        self.assertEqual(p.z, 12)
        assert_array_equal(p.points, (10, 12))


if __name__ == "__main__":
    unittest.main()
