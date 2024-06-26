import unittest
import pathlib
from spdm.core.file import File

xml_file = pathlib.Path(__file__).parent.joinpath("data/pf_active.xml")


class TestFileXML(unittest.TestCase):

    def test_create(self):
        file = File(xml_file)
        self.assertEqual(file.__class__.__name__, "FileXML")
        entry = file.read()
        self.assertEqual(entry.__class__.__name__, "EntryXML")

    def test_read(self):
        entry = File(xml_file).read()

        self.assertEqual(entry.child("coil/0/name").value, "PF1")

    def test_iter(self):

        entry = File(xml_file).read()

        name_list = [v.child("name").value for v in entry.child("coil")]

        name_list_expect = [
            "PF1",
            "PF2",
            "PF3",
            "PF4",
            "PF5",
            "PF6",
            "PF7",
            "PF8",
            "PF9",
            "PF10",
            "PF11",
            "PF12",
            "PF13",
            "PF14",
            "IC1",
            "IC2",
        ]

        self.assertListEqual(name_list, name_list_expect)

    def test_exists(self):
        entry = File(xml_file).read()

        self.assertTrue(entry.child("coil/0/name").exists)
        self.assertFalse(entry.child("coil/0/key").exists)

    def test_count(self):
        entry = File(xml_file).read()
        self.assertEqual(entry.child("coil").count, 16)


if __name__ == "__main__":
    unittest.main()
