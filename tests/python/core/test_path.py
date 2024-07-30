import unittest
from copy import deepcopy
from spdm.core.path import Path, Query
from spdm.utils.tags import _not_found_


class TestPath(unittest.TestCase):
    def test_init(self):
        p = ["a", "b", {"c": slice(4, 10, 2)}]
        self.assertEqual(Path(p)[:2], p[:2])
        self.assertIsInstance(Path(p)[-1], Query)
        self.assertEqual(Path(p)[-1]._query["c"], p[-1]["c"])

    def test_parser(self):
        self.assertEqual(Path.parser("a/b/c"), ["a", "b", "c"])
        self.assertEqual(Path.parser("a/b/c/0"), ["a", "b", "c", 0])
        self.assertEqual(Path.parser("a/b/c/0/d"), ["a", "b", "c", 0, "d"])

        self.assertEqual(Path.parser("a[(1,2,3,'a')]/h"), ["a", (1, 2, 3, "a"), "h"])
        self.assertEqual(Path.parser("a[{1,2,3,'a'}]/h"), ["a", {1, 2, 3, "a"}, "h"])
        # self.assertEqual(Path._parser("a[{'$le':[1,2]}]/h"), ["a", {Path.tags.le: [1, 2]}, "h"])
        # self.assertEqual(Path._parser("a[1:10:-3]/h"),       ["a", slice(1, 10, -3), "h"])
        # self.assertEqual(Path._parser("a[1:10:-3]/$next"),   ["a", slice(1, 10, -3), Path.tags.next])

    def test_append(self):
        p = Path()
        p.append("a/b/c")

        self.assertEqual(p[:], ["a", "b", "c"])

    data = {
        "a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4],
        "c": "I'm {age}!",
        "d": {"e": "{name} is {age}", "f": "address"},
    }

    def test_get(self):
        # fmt:off
        self.assertEqual(Path("c"       ).get(self.data), self.data["c"])
        self.assertEqual(Path("d/e"     ).get(self.data), self.data["d"]["e"])
        self.assertEqual(Path("d/f"     ).get(self.data), self.data["d"]["f"])
        self.assertEqual(Path("a/0"     ).get(self.data), self.data["a"][0])
        self.assertEqual(Path(["a", 1]  ).get(self.data), self.data["a"][1])
        # self.assertEqual(Path("a/2:4:1").query(self.data),        self.data["a"][2:4])
        self.assertEqual(Path("d/k"     ).get(self.data, default_value=None), None)
        # fmt:on

    def test_get_many(self):
        cache = deepcopy(self.data)

        res = Path({"a/2", "c", "d/e", "e"}).get(cache)

        self.assertDictEqual(res, {"a/2": cache["a"][2], "c": cache["c"], "d/e": cache["d"]["e"], "e": _not_found_})

    def test_query(self):
        # fmt:off
        self.assertEqual(Path("a"   ).query(self.data, Query.count), 6)
        self.assertEqual(Path("d/e" ).query(self.data, Query.count), 1)
        self.assertEqual(Path("b/h" ).query(self.data, Query.count), 0)
        self.assertEqual(Path("d/f" ).query(self.data, Query.count), 1)
        self.assertEqual(Path(      ).query(self.data, Query.count), 3)
        self.assertEqual(Path("a"   ).query(self.data, Query.count), 6)
        self.assertEqual(Path("d"   ).query(self.data, Query.count), 2)
        # fmt:on

        # self.assertTrue(Path(["a", slice(2, 7), {Path.tags.equal: [1, 2, 3, 4]}]).query(self.data))

    def test_insert(self):
        cache = {}

        Path("a").insert(cache, "hello world {name}!")
        self.assertEqual(cache["a"], "hello world {name}!")

        Path("e/f").insert(cache, 5)
        Path("e/g").insert(cache, 6)

        self.assertEqual(cache["e"]["f"], 5)
        self.assertEqual(cache["e"]["g"], 6)

        cache = deepcopy(self.data)

        Path("c").insert(cache, {"a": "hello world", "b": 3.141567})
        Path("c").insert(cache, 1.23455)

        self.assertEqual(cache["c"][0], "I'm {age}!")
        # self.assertEqual(cache["c"][1]["a"], "hello world")
        # self.assertEqual(cache["c"][1]["b"], 3.141567)
        self.assertEqual(cache["c"][-1], 1.23455)

    def test_update(self):
        cache = deepcopy(self.data)

        Path().update(cache, {"d": {"g": 5, "f": 6}})

        self.assertEqual(cache["d"]["e"], "{name} is {age}")

        self.assertEqual(cache["d"]["f"], 6)

        self.assertEqual(cache["d"]["g"], 5)

    def test_update_many(self):
        cache = deepcopy(self.data)

        Path({"a/2", "c", "d/e", "e"}).update(cache, True)

        self.assertTrue(cache["a"][2])
        self.assertTrue(cache["c"])
        self.assertTrue(cache["d"]["e"])

    def test_delete(self):
        cache = {"a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4], "b": "hello world!"}

        Path("b").delete(cache)
        Path("a/1").delete(cache)
        self.assertTrue("b" not in cache)
        self.assertEqual(cache["a"], ["hello world {name}!", 1, 2, 3, 4])

    def test_sequence_tag(self):
        cache = {
            "people": [
                {"name": "zhangsan", "age": 10, "address": "beijing"},
                {"name": "lisi", "age": 20, "address": "shanghai"},
                {"name": "wangwu", "age": 30, "address": "guangzhou"},
                {"name": "zhaoliu", "age": 40, "address": "shenzhen"},
            ]
        }

        self.assertEqual(Path("people/zhangsan/age").get(cache), 10)
        self.assertEqual(Path("people/lisi/age").get(cache), 20)

        Path("people/lisi/age").put(cache, 70)
        self.assertEqual(Path("people/lisi/age").get(cache), 70)

    def test_find_many(self):

        res = Path(("a/2", "c", "d/e", "e")).find(self.data, default_value=_not_found_)

        self.assertListEqual(list(res), [self.data["a"][2], self.data["c"], self.data["d"]["e"], _not_found_])


if __name__ == "__main__":
    unittest.main()
