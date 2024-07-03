import unittest

import numpy as np
from scipy import constants
from spdm.utils.logger import logger
from spdm.core.mesh import Mesh


class TestMesh(unittest.TestCase):

    def test_null_mesh(self):
        mesh = Mesh()
        self.assertIsInstance(mesh, Mesh)

        self.assertTrue(mesh.geometry.is_null)

    def test_structured_mesh(self):
        from spdm.mesh.mesh_structured import StructuredMesh

        mesh = Mesh(dim1=np.linspace(0, 1, 10), dim2=np.linspace(1, 2, 20), mesh_type="structured")
        self.assertIsInstance(mesh, StructuredMesh)
        self.assertEqual(mesh.rank, 2)
        self.assertEqual(mesh.ndim, 2)

    def test_uniform_mesh(self):
        from spdm.mesh.mesh_uniform import UniformMesh

        mesh = Mesh({"@type": "uniform"})
        self.assertIsInstance(mesh, UniformMesh)


if __name__ == "__main__":
    unittest.main()
