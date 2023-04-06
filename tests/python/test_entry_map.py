import unittest
from copy import deepcopy
from logging import log

from spdm.util.logger import logger
from spdm.common.tags import _not_found_
from spdm.data.Entry import Entry, EntryCombine
from spdm.data.Path import Path
from spdm.data.Query import Query
from spdm.data.Mapper import EntryMapper, PathMapper


class TestEntryMap(unittest.TestCase):
    data = {
        "a": [
            "hello world {name}!",
            "hello world2 {name}!",
            1, 2, 3, 4
        ],
        "c": "I'm {age}!",
        "d": {
            "e": "{name} is {age}",
            "f": "{address}"
        }
    }
    mapping = """<?xml version="1.0" ?>
    <root>
        <first> a/0 </first>
        <second> a/1 </second>
        <others> c/2:5 </others>
        <words>
            <address>
               [c,d/e,d/f]
            </address>
        </words>
    </root>
    """

    def test_mapping_path(self):
        pathmapper = PathMapper(Entry.create(self.mapping, scheme="XML"))

        self.assertEqual((pathmapper/"first").as_request(), "a/0")
        self.assertEqual((pathmapper/"second").as_request(), "a/1")
        self.assertEqual((pathmapper/"others").as_request(), "c/2:5")
        self.assertEqual((pathmapper/"words/address").as_request(), "[c,d/e,d/f]")

    def test_get(self):
        entry = EntryMapper(self.data, PathMapper(Entry.create(self.mapping, scheme="XML")))
        self.assertEqual(entry.get("first"), self.data["a"][0])
        self.assertEqual(entry.get("second"), self.data["a"][1])
        self.assertEqual(entry.get("others"), self.data["c"][2:5])


if __name__ == '__main__':
    unittest.main()
