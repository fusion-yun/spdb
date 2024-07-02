import unittest
import pathlib
from spdm.core.file import File

xml_file = pathlib.Path(__file__).parent.joinpath("data/pf_active.xml")


class TestFileXML(unittest.TestCase):

    def test_create(self):
        with File(xml_file) as entry:
            self.assertEqual(entry.__class__.__qualname__, "FileXML.Entry")
        with File(xml_file, format="xml") as entry:
            self.assertEqual(entry.__class__.__qualname__, "FileXML.Entry")

    def test_read(self):
        entry = File(xml_file).entry

        self.assertEqual(entry.child("coil/0/name").value, "PF1")

    def test_exists(self):
        entry = File(xml_file).entry

        self.assertTrue(entry.child("coil/0/name").exists)
        self.assertFalse(entry.child("coil/0/key").exists)

    def test_count(self):
        entry = File(xml_file).entry
        self.assertEqual(entry.child("coil").count, 16)

    def test_search(self):
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

        with File(xml_file) as entry:
            name_list = [*entry.child("coil/*/name").for_each()]
            self.assertListEqual(name_list, name_list_expect)


if __name__ == "__main__":
    unittest.main()
