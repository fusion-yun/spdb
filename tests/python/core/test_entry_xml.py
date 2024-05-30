import unittest
from copy import deepcopy
import pathlib
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.core.entry import Entry, as_value
from spdm.core.file import File
xml_file = pathlib.Path(__file__).parent.joinpath("pf_active.xml")


class TestXMLEntry(unittest.TestCase):

    def test_read(self):
        entry = File(xml_file).read()

        self.assertEqual(entry.child("coil/0/name").__value__, "PF1")

    def test_iter(self):

        entry = File(xml_file).read()

        name_list = ([v.child('name').__value__ for v in entry.child("coil")])

        name_list_expect = ['PF1', 'PF2', 'PF3', 'PF4', 'PF5', 'PF6', 'PF7', 'PF8',
                            'PF9', 'PF10', 'PF11', 'PF12', 'PF13', 'PF14', 'IC1', 'IC2']

        self.assertListEqual(name_list, name_list_expect)

    def test_exists(self):
        entry = File(xml_file).read()

        self.assertTrue(entry.child("coil/0/name").exists)
        self.assertFalse(entry.child("coil/0/key").exists)

    def test_count(self):
        entry = File(xml_file).read()
        self.assertEqual(entry.child("coil").count, 16)


if __name__ == '__main__':
    unittest.main()
