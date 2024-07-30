import unittest

from numpy.testing import assert_array_equal


from spdm.geometry.point import Point


class TestPoint(unittest.TestCase):

    def test_classgetitem(self):

        p = Point(10, 12)

        self.assertEqual(p.__class__.__name__, "Point")
        self.assertEqual(p.ndim, 2)
        self.assertEqual(p.rank, 0)
        self.assertEqual(p.points[0], 10)
        self.assertEqual(p.points[1], 12)
        assert_array_equal(p.points, (10, 12))


if __name__ == "__main__":
    unittest.main()
