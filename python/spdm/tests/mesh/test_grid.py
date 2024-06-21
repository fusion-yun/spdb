import unittest

import numpy as np
from scipy import constants
from spdm.utils.logger import logger
from spdm.core.mesh import Mesh


class TestMesh(unittest.TestCase):

    def test_nullMesh(self):
        Mesh = Mesh()
        self.assertEqual(Mesh.type, None)
        self.assertEqual(Mesh.units, ["-"])
        self.assertEqual(Mesh.geometry, None)

    def test_structured_Mesh(self):
        from spdm.mesh.mesh_structured import StructuredMesh

        self.assertRaisesRegexp(
            TypeError, "Can't instantiate abstract class StructuredMesh with abstract method geometry", StructuredMesh, [10, 10])

    def test_uniform_mesh(self):
        Mesh = Mesh("uniform")
        self.assertEqual(Mesh.type, "uniform")
        self.assertEqual(Mesh.units, ["-"])
        self.assertEqual(Mesh.geometry, None)


if __name__ == '__main__':
    unittest.main()
