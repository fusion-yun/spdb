import unittest

import numpy as np
from numpy.testing import assert_array_equal
import scipy


from spdm.utils.logger import logger
from spdm.core.mesh import Mesh
from spdm.geometry.box import Box

TWOPI = scipy.constants.pi * 2.0


class TestMesh(unittest.TestCase):

    # def test_null_mesh(self):
    #     mesh = Mesh()
    #     self.assertIsInstance(mesh, Mesh)
    #     self.assertTrue(mesh.is_null)

    def test_structured_mesh(self):
        from spdm.mesh.mesh_rectilinear import RectilinearMesh

        mesh = RectilinearMesh(np.linspace(0, 1, 10), np.linspace(1, 2, 20))
        self.assertIsInstance(mesh, RectilinearMesh)
        assert_array_equal(mesh.shape, (10, 20))
        self.assertIsInstance(mesh.geometry, Box)
        self.assertEqual(mesh.geometry.rank, 2)
        self.assertEqual(mesh.geometry.ndim, 2)
        self.assertEqual(mesh.rank, 2)
        self.assertEqual(mesh.ndim, 2)

    def test_uniform_mesh(self):
        from spdm.mesh.mesh_uniform import UniformMesh

        mesh = Mesh({"@type": "uniform"})
        self.assertIsInstance(mesh, UniformMesh)

    def test_rectilinear_mesh(self):
        from spdm.mesh.mesh_rectilinear import RectilinearMesh

        x = np.linspace(0, 1 * TWOPI, 128)
        y = np.linspace(0, 2 * TWOPI, 128)

        mesh = RectilinearMesh(x, y)

        g_x, g_y = np.meshgrid(x, y, indexing="ij")

        assert_array_equal(mesh.points[0], g_x)
        assert_array_equal(mesh.points[1], g_y)


if __name__ == "__main__":
    unittest.main()
