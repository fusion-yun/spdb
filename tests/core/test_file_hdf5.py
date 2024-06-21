import pathlib
import shutil
import tempfile
import unittest

import h5py
import numpy as np
from spdm.core.file import File
from spdm.utils.logger import logger

SP_TEST_DATA_DIRECTORY = pathlib.Path("../data")


class TestFileHDF5(unittest.TestCase):
    data = {
        "a": [
            "hello world {name}!",
            "hello world2 {name}!",
        ],
        "b": [1.0, 2, 3, 4],
        "c": "I'm {age}!",
        "d": {
            "e": "{name} is {age}",
            "f": "{address}",
            "g": {"a": 1, "b": 2}
        },
        "h": np.random.random([7, 9])
    }

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory(prefix="spdm_")
        self.temp_dir = pathlib.Path(self._temp_dir.name)
        shutil.copy(SP_TEST_DATA_DIRECTORY/"test_hdf5_in.h5", self.temp_dir/"test_hdf5_in.h5")

        return super().setUp()

    def tearDown(self) -> None:
        self.temp_dir = None
        self._temp_dir.cleanup()
        del self._temp_dir
        return super().tearDown()

    def test_read(self):
        f_name = self.temp_dir / "test_hdf5_in.h5"

        h5file = h5py.File(f_name)

        first = h5file.keys()

        with File(f_name, mode="r") as f_in:
            second = f_in.read().dump()

    def test_write(self):
        f_name = self.temp_dir / "test_out.h5"
        with File(f_name, mode="w") as f_out:
            f_out.write(self.data)

        self.assertListEqual(list(res.get("a")), self.data["a"])
        self.assertListEqual(list(res.get("b")), self.data["b"])
        self.assertEqual(res.get("d.e"), self.data["d"]["e"])

        self.assertDictEqual(res.get("d"), self.data["d"])

        self.assertTrue(np.array_equal(res.get("h"), self.data["h"]))


if __name__ == '__main__':
    unittest.main()
