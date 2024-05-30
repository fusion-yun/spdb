import unittest
from copy import deepcopy

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.core.entry import Entry, as_value


class TestEntry(unittest.TestCase):
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

    def test_get(self):

        d = Entry(self.data)

        self.assertEqual(d.get("c"),           self.data["c"])
        self.assertEqual(d.get("d/e"),      self.data["d"]["e"])
        self.assertEqual(d.get("d/f"),      self.data["d"]["f"])
        self.assertEqual(d.get("a/0"),        self.data["a"][0])
        self.assertEqual(d.get("a/1"),        self.data["a"][1])

    def test_exists(self):
        d = Entry(self.data)

        self.assertTrue(d.exists)
        self.assertTrue(d.child("a").exists)
        self.assertTrue(d.child("d/e").exists)
        self.assertFalse(d.child("b/h").exists)
        self.assertFalse(d.child("f/g").exists)

    def test_count(self):
        d = Entry(self.data)

        self.assertEqual(d.count,          1)
        self.assertEqual(d.child("a").count,   6)
        self.assertEqual(d.child("d").count,   1)

    def test_insert(self):
        cache = deepcopy(self.data)
        d = Entry(cache)

        d.child("c").insert(1.23455)

        d.child("c").insert([{"a": "hello world", "b": 3.141567}])

        self.assertEqual(cache["c"][1],                      1.23455)
        self.assertEqual(cache["c"][2]["a"],           "hello world")
        self.assertEqual(cache["c"][2]["b"],                3.141567)

    def test_update(self):
        cache = deepcopy(self.data)

        d = Entry(cache)

        d.update({"d": {"g": 5}})

        self.assertEqual(cache["d"]["e"], "{name} is {age}")
        self.assertEqual(cache["d"]["f"], "{address}")
        self.assertEqual(cache["d"]["g"], 5)

    def test_erase(self):
        cache = {
            "a": [
                "hello world {name}!",
                "hello world2 {name}!",
                1, 2, 3, 4
            ],
            "b": "hello world!"
        }

        d = Entry(cache)
        del d["b"]
        self.assertTrue("b" not in cache)

    def test_get_many(self):
        cache = deepcopy(self.data)

        d = Entry(cache)

        self.assertEqual(d.child('a/2').__value__, self.data['a'][2])

        res = d.get({"a/2", "c",  "d/e", "e"})

        self.assertDictEqual(res, {"a/2": cache['a'][2],
                                   "c": cache['c'],
                                   "d/e":   cache['d']['e'],
                                   "e": _not_found_})

    def test_iter(self):
        data = [1, 2, 3, 4, 5]

        d0 = Entry(data)

        self.assertListEqual([v for v in d0.for_each()], data)

    def test_find_next(self):
        data = [1, 2, 3, 4, 5]

        d0 = Entry(data)

        res = []

        next_id = []

        while True:
            value, next_id = d0.find_next(*next_id)
            if next_id is None or len(next_id) == 0:
                break
            res.append(value)

        self.assertListEqual(res, data)


if __name__ == '__main__':
    unittest.main()
