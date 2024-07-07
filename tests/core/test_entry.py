import unittest
from copy import deepcopy

from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger
from spdm.core.entry import Entry, open_entry
from spdm.core.query import Query


class TestEntry(unittest.TestCase):
    data = {
        "a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4],
        "c": "I'm {age}!",
        "d": {"e": "{name} is {age}", "f": "{address}"},
    }

    def test_get(self):

        d = Entry(deepcopy(self.data))

        self.assertEqual(d.get("c"), self.data["c"])
        self.assertEqual(d.get("d/e"), self.data["d"]["e"])
        self.assertEqual(d.get("d/f"), self.data["d"]["f"])
        self.assertEqual(d.get("a/0"), self.data["a"][0])
        self.assertEqual(d.get("a/1"), self.data["a"][1])

    def test_exists(self):
        d = Entry(deepcopy(self.data))

        self.assertTrue(d.exists)
        self.assertTrue(d.child("a").exists)
        self.assertTrue(d.child("d/e").exists)
        self.assertFalse(d.child("b/h").exists)
        self.assertFalse(d.child("f/g").exists)

    def test_count(self):
        d = Entry(deepcopy(self.data))

        self.assertEqual(d.count, 3)
        self.assertEqual(d.child("a").count, 6)
        self.assertEqual(d.child("d").count, 2)

    def test_insert(self):
        cache = deepcopy(self.data)

        d = Entry(cache)

        d.child("c").insert(1.23455)

        d.child("c").insert({"a": "hello world", "b": 3.141567})

        self.assertEqual(cache["c"][1], 1.23455)
        self.assertEqual(cache["c"][2]["a"], "hello world")
        self.assertEqual(cache["c"][2]["b"], 3.141567)

    def test_update(self):
        cache = deepcopy(self.data)

        d = Entry(cache)

        d.update({"d": {"g": 5}})

        self.assertEqual(cache["d"]["e"], "{name} is {age}")
        self.assertEqual(cache["d"]["f"], "{address}")
        self.assertEqual(cache["d"]["g"], 5)

    def test_delete(self):
        cache = {"a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4], "b": "hello world!"}

        d = Entry(cache)
        d.child("b").delete()
        self.assertTrue("b" not in cache)

    def test_get_many(self):
        cache = deepcopy(self.data)

        d = Entry(cache)

        self.assertEqual(d.child("a/2").value, self.data["a"][2])

        res = d.get({"a/2", "c", "d/e", "e"})

        self.assertDictEqual(res, {"a/2": cache["a"][2], "c": cache["c"], "d/e": cache["d"]["e"], "e": _not_found_})

    def test_search(self):
        data1 = [1, 2, 3, 4, 5]
        d1 = Entry(data1)
        self.assertListEqual([*d1.search()], data1)

        d1 = Entry([{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}])

        self.assertListEqual([*d1.child("*/id").search()], data1)

        data2 = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        d2 = Entry(data2)

        self.assertSetEqual(set([*d2.search(Query.tags.get_key)]), set([*data2.keys()]))
        self.assertSetEqual(set([*d2.search(Query.tags.get_value)]), set([*data2.values()]))
        self.assertDictEqual({kv[0]: kv[1] for kv in d2.search(Query.tags.get_item)}, data2)

        data3 = [{"name": "John", "age": 20}, {"name": "Jane", "age": 30}, {"name": "Jack", "age": 40}]
        d3 = Entry(data3)
        self.assertSetEqual({k for k in d3.child("*/name").search()}, {"John", "Jane", "Jack"})


if __name__ == "__main__":
    unittest.main()
