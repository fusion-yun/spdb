import pathlib
import shutil
import tempfile
import unittest

import h5py
import numpy as np
from spdm.core.file import File
from spdm.core.entry import Entry
from spdm.utils.logger import logger

SP_TEST_DATA_DIRECTORY = pathlib.Path("../data")


test_data = {
    "a": [
        "hello world {name}!",
        "hello world2 {name}!",
    ],
    "b": [1.0, 2, 3, 4],
    "c": "I'm {age}!",
    "d": {"e": "{name} is {age}", "f": "{address}", "g": {"a": 1, "b": 2}},
    "h": np.random.random([7, 9]),
}


class TestFileHDF5(unittest.TestCase):

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory(prefix="spdm_")
        self.temp_dir = pathlib.Path(self._temp_dir.name)
        # shutil.copy(SP_TEST_DATA_DIRECTORY/"test_hdf5_in.h5", self.temp_dir/"test_hdf5_in.h5")

    #     return super().setUp()

    def tearDown(self) -> None:
        self.temp_dir = None
        self._temp_dir.cleanup()
        del self._temp_dir
        return super().tearDown()

    def test_read(self):

        f_name = self.temp_dir / "test_hdf5_in.h5"

        with h5py.File(f_name, mode="x") as h5file:
            data_in = np.random.rand(10, 15)
            h5file.create_dataset("data", data=data_in)

        with File(f_name, mode="r", scheme="hdf5") as f_in:
            data_out = f_in.get("data")

        self.assertTrue(np.allclose(data_in, data_out))

    def test_write(self):
        f_name = self.temp_dir / "test_hdf5_out.h5"
        with File(f_name, mode="w", scheme="hdf5") as f_out:
            f_out.write(test_data)

        with h5py.File(f_name, mode="r") as h5file:
            self.assertTrue(np.allclose(h5file["h"], test_data["h"]))
            self.assertEqual(h5file.attrs["c"], test_data["c"])
            self.assertEqual(h5file["d"].attrs["f"], test_data["d"]["f"])
            self.assertTrue(np.allclose(h5file["b"], test_data["b"]))

            # self.assertListEqual(list(res.get("b")), test_data["b"])
            # self.assertEqual(res.get("d.e"), test_data["d"]["e"])

            # self.assertDictEqual(res.get("d"), test_data["d"])

            # self.assertTrue(np.array_equal(res.get("h"), test_data["h"]))


if __name__ == "__main__":
    unittest.main()
