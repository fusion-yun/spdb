import unittest

import numpy as np
from scipy import constants
from spdm.utils.logger import logger
from spdm.core.mesh import Mesh


class TestMesh(unittest.TestCase):

    def test_null_mesh(self):
        mesh = Mesh()
        self.assertIsInstance(mesh, Mesh)
        self.assertEqual(mesh.units, tuple(["-"]))
        self.assertEqual(mesh.geometry, None)

    def test_structured_mesh(self):
        from spdm.mesh.mesh_structured import StructuredMesh

        mesh = Mesh("structured")
        self.assertIsInstance(mesh, StructuredMesh)
        # self.assertRaisesRegexp(
        #     TypeError,
        #     "Can't instantiate abstract class StructuredMesh with abstract method geometry",
        #     StructuredMesh,
        #     [10, 10],
        # )

    def test_uniform_mesh(self):
        from spdm.mesh.mesh_uniform import UniformMesh

        mesh = Mesh("uniform")
        self.assertIsInstance(mesh, UniformMesh)
        self.assertEqual(mesh.units, ["-"])
        self.assertEqual(mesh.geometry, None)


if __name__ == "__main__":
    unittest.main()
