import unittest

from numpy.testing import assert_array_equal


from spdm.core.geo_object import GeoObject


class TestGeoObject(unittest.TestCase):

    def test_define_new_class(self):

        class GObj(GeoObject, rank=1, name="gobj"):

            @property
            def rank(self) -> int:
                return 10

        obj = GObj(10, 10)

        self.assertEqual(GObj._metadata.get("name", None), "gobj")
        self.assertEqual(obj.rank, 10)

    def test_classgetitem(self):
        class Point(GeoObject, rank=0):
            pass

        PointRZ = Point["RZ"]

        p = PointRZ(10, 12)
        self.assertEqual(PointRZ.__name__, "PointRZ2D")
        self.assertEqual(p.ndim, 2)
        self.assertEqual(p.rank, 0)
        assert_array_equal(p.points, (10, 12))
        self.assertEqual(p.r, 10)
        self.assertEqual(p.z, 12)


if __name__ == "__main__":
    unittest.main()
