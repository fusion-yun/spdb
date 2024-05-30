
from typing import List
from spdm.core.query import Query
from spdm.core.path import Path
from spdm.core.entry import Entry, EntryCombine
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger
import pathlib
import sys
import unittest
import numpy as np


class TestEntryCombiner(unittest.TestCase):
    data = [
        {"id": 0,
            "value": 1.23,
            "c": "I'm {age}!",
            "d": {"e": "{name} is {age}", "f": "{address}", "g": [1, 2, 3]}},
        {"id": 1,
            "c": "I'm {age}!",
            "d": {"e": "{name} is {age}", "f": "{address}"}},
        {"id": 2,
            "value": 4.23,
            "c": "I'm {age}!",
            "d": {"e": "{name} is {age}", "f": "{address}", "g": [4, 5, 7]}}
    ]
    atoms = [
        {"label": "H", "z": 1, "element": [{"a": 1, "z_n": 1, "atoms_n": 1}], },
        {"label": "D", "z": 1, "element": [{"a": 2, "z_n": 1, "atoms_n": 1}], },
        {"label": "T", "z": 1, "element": [{"a": 3, "z_n": 1, "atoms_n": 1}], },
    ]
    models = [
        {
            "code": {"name": "dummy0"},
            "profiles_1d": {"ion": atoms}
        },
        {
            "code": {"name": "dummy1"},
            "profiles_1d": {
                "ion": [
                    {"label": "H", "density": np.random.random(128)},
                    {"label": "D", },
                    {"label": "T", "density":  np.random.random(128)},
                ]
            }
        },
        {
            "code": {"name": "dummy2"},
            "profiles_1d": {
                "ion": [
                    {"label": "D", "density": np.random.random(128)},
                    {"label": "T", "temperature": np.random.random(128)},
                    {"label": "H", "density": np.random.random(128)},
                ]
            }
        },

    ]

    # def test_get(self):
    #     d = EntryCombine(self.data)
    #     self.assertEqual(d.child("value").pull(), sum([v.get("value", 0.0) for v in self.data]))
    #     self.assertEqual(d.child("d.g").pull(), self.data[0]["d"]["g"]+self.data[2]["d"]["g"])

    def test_combine(self):
        models = [
        {
            "code": {"name": "dummy1"},
            "profiles_1d": {
                "ion": [
                    {"label": "H", "density": np.random.random(128)},
                    {"label": "D", },
                    {"label": "T", "density":  np.random.random(128)},
                ]
            }
        },
        {
            "code": {"name": "dummy2"},
            "profiles_1d": {
                "ion": [
                    {"label": "D", "density": np.random.random(128)},
                    {"label": "T", "temperature": np.random.random(128)},
                    {"label": "H", "density": np.random.random(128)},
                ]
            }
        },

    ]
        d = List(models)
        self.assertTrue(np.array_equal(
                 d["profiles_1d", "ion", Query(label="H"), "density"].combine.value,
                        models[1]["profiles_1d"]["ion"][0]["density"] +
                        models[2]["profiles_1d"]["ion"][2]["density"])
                        )

    # def test_cache(self):
    #     cache = {}
    #     d = EntryCombiner(self.data )
    #     expected = sum([d["value"] for d in self.data])

    #     c = d.extend("value")
    #     self.assertEqual(c.pull(), expected)
    #     self.assertEqual(cache["value"], expected)
    #     c.push(5)
    #     self.assertEqual(cache["value"], 5)

    #     d.extend("test_cache").push("just test cache")
    #     self.assertEqual(d.get("test_cache",default_value=_undefined_), _undefined_)
    #     self.assertEqual(d.get("test_cache"), cache["test_cache"])

# class TestEntryWrapper(unittest.TestCase):
#     data = [
#         {"id": 0,
#          "value": 1.23,
#          "c": "I'm {age}!",
#          "d": {"e": "{name} is {age}", "f": "{address}", "g": [1, 2, 3]}},
#         {"id": 1,
#          "value": 2.23,
#          "c": "I'm {age}!",
#          "d": {"e": "{name} is {age}", "f": "{address}"}},
#         {"id": 2,
#          "value": 4.23,
#          "c": "I'm {age}!",
#          "d": {"e": "{name} is {age}", "f": "{address}", "g": [4, 5, 7]}}
#     ]

#     def test_get(self):
#         entry = Entry(self.data)
#         d = EntryWrapper(entry)

#     def test_property(self):
#         entry = Entry(self.data)
#         d = EntryWrapper(entry)

#     def test_put(self):
#         entry = Entry(self.data)
#         d = EntryWrapper(entry)

#     def test_erase(self):
#         entry = Entry(self.data)
#         d = EntryWrapper(entry)

#     def test_cache(self):
#         entry = Entry(self.data)
#         d = EntryWrapper(entry)
#     #     d = Entry(cache)

#     #     d.extend("a").put("hello world {name}!")
#     #     self.assertEqual(cache["a"], "hello world {name}!")

#     #     d["c"][_next_] = 1.23455
#     #     d["c"][_next_] = {"a": "hello world", "b": 3.141567}

#     #     self.assertEqual(cache["c"][0],  1.23455)
#     # def test_append(self):
#     #     d = Entry()
#     #     d.extend(_next_).put({"a": 1, "b": 2})

#     #     self.assertEqual(d.count, 1)
#     #     # self.assertTrue(d.__category__ | Entry.Category.LIST)
#     #     self.assertEqual(d.extend([0, "a"]).get(), 1)
#     #     self.assertEqual(d.extend([0, "b"]).get(), 2)


if __name__ == '__main__':
    unittest.main()
