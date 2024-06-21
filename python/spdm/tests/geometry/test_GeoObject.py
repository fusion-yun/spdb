
import typing
import unittest
from copy import deepcopy

import numpy as np

from spdm.utils.logger import logger

from spdm.core.geo_object import GeoObject, GeoObject1D, GeoObject2D, GeoObject3D


class TestGeoObject(unittest.TestCase):

    def test_define_new_class(self):

        class GObj(GeoObject1D):

            @property
            def rank(self) -> int: return 10

        obj = GObj(np.zeros((10, 10)))

        self.assertEqual(obj.rank, 10)


if __name__ == '__main__':
    unittest.main()
