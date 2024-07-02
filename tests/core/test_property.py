import unittest
from spdm.core.htree import List
from spdm.core.property_tree import PropertyTree


class TestPropertyTree(unittest.TestCase):
    def test_get(self):
        cache = {
            "time": [0.0],
            "vacuum_toroidal_field": {"r0": 6.2, "b0": [-5.3]},
            "code": {
                "name": "eq_analyze",
            },
            "time_slice": [
                {
                    "profiles_2d": {"grid": {"dim1": 129, "dim2": 257}},
                    "boundary": {"psi_norm": 0.99},
                    "coordinate_system": {"grid": {"dim1": 256, "dim2": 128}},
                }
            ],
        }
        ptree = PropertyTree(cache)

        self.assertEqual(ptree.time[0], 0.0)
        self.assertEqual(ptree.vacuum_toroidal_field.r0, 6.2)
        self.assertEqual(ptree.time_slice[0].profiles_2d.grid.dim1, 129)

    def test_set(self):
        cache = {}
        ptree = PropertyTree(cache)
        ptree.time_slice = []
        self.assertIsInstance(ptree.time_slice, List[PropertyTree])
        ptree.time_slice[0].profiles_2d = {"grid": {"dim1": 129}}
        self.assertEqual(cache["time_slice"][0]["profiles_2d"]["grid"]["dim1"], 129)
