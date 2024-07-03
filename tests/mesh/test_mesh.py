import unittest

import numpy as np

from spdm.utils.logger import logger
from spdm.core.mesh import Mesh
from spdm.geometry.box import Box


class TestMesh(unittest.TestCase):

    def test_null_mesh(self):
        mesh = Mesh()
        self.assertIsInstance(mesh, Mesh)
        self.assertTrue(mesh.is_null)

    def test_structured_mesh(self):
        from spdm.mesh.mesh_structured import StructuredMesh

        mesh = Mesh(np.linspace(0, 1, 10), np.linspace(1, 2, 20), mesh_type="rectilinear")
        self.assertIsInstance(mesh, StructuredMesh)
        self.assertEqual(mesh.shape, (10, 20))
        self.assertIsInstance(mesh.geometry, Box)
        self.assertEqual(mesh.geometry.rank, 2)
        self.assertEqual(mesh.geometry.ndim, 2)
        self.assertEqual(mesh.rank, 2)
        self.assertEqual(mesh.ndim, 2)

    def test_uniform_mesh(self):
        from spdm.mesh.mesh_uniform import UniformMesh

        mesh = Mesh({"@type": "uniform"})
        self.assertIsInstance(mesh, UniformMesh)


if __name__ == "__main__":
    unittest.main()
