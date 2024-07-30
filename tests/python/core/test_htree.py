import typing
import unittest
from copy import deepcopy

import numpy as np

from spdm.core.htree import Dict, List, HTreeNode, HTree
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger


class Foo(Dict):
    pass


test_data = {
    "a": ["hello world {name}!", "hello world2 {name}!", 1.0, 2, 3, 4],
    "c": "I'm {age}!",
    "d": {"e": "{name} is {age}", "f": "{address}"},
}


class NamedFoo(Dict):
    a: List[typing.Any]
    c: str
    d: Dict


class TestHTree(unittest.TestCase):
    def test_null(self):

        self.assertTrue(HTreeNode().__empty__())
        self.assertFalse(HTreeNode().__null__())

    def test_new_dict(self):
        d = Dict(first=1, second=2, name="hello")
        self.assertEqual(d["first"], 1)
        self.assertEqual(d["second"], 2)
        self.assertEqual(d["name"], "hello")

    def test_new_list(self):
        d = List([1, 2, 3, 4])

        self.assertEqual(d[0], 1)
        self.assertEqual(d[1], 2)
        self.assertEqual(d[2], 3)
        self.assertEqual(d[3], 4)

    def test_get_child(self):
        cache = {
            "a": "hello",
            "b": 1.2345,
            "c": np.ones([10, 20]),
            "d": [1, 2, 3, 4, 5],
            "e": {"a": 1, "b": 2, "c": 3},
        }
        d = HTree(cache)

        self.assertEqual(d["a"], cache["a"])
        self.assertEqual(d["b"], cache["b"])
        self.assertIs(d["c"], cache["c"])

        # self.assertTrue(isinstance(d["d"], List))
        # self.assertTrue(isinstance(d["e"], Dict))

        # self.assertEqual(len(n) == 0)

    def test_type_hint(self):
        d1 = List[Dict]()

        d1.insert({"a": 1, "b": 2})

        self.assertIsInstance(d1[0], Dict)

        # self.assertEqual(len(d1), 1)
        self.assertEqual(d1[0]["a"], 1)
        self.assertEqual(d1[0]["b"], 2)

        data = [1, 2, 3, 4, 5]

        class Foo:
            def __init__(self, v) -> None:
                self.v = v

        d1 = List[Foo](deepcopy(data))

        self.assertIsInstance(d1[2], Foo)
        self.assertEqual(d1[2].v, data[2])

    # data = {
    #     "a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4],
    #     "c": "I'm {age}!",
    #     "d": {"e": "{name} is {age}", "f": "{address}"},
    # }

    # # def test_create(self):
    # #     cache = []
    # #     d = HTree(cache)
    # #     self.assertEqual(d.create_child("hello"), "hello")
    # #     self.assertEqual(d.create_child(1), 1)
    # #     v = np.ones([10, 20])
    # #     self.assertIs(d.create_child(v), v)
    # #     self.assertTrue(isinstance(d.create_child("hello", always_node=True), Node))

    # #     self.assertTrue(isinstance(d.create_child([1, 2, 3, 4, 5]), List))
    # #     self.assertTrue(isinstance(d.create_child((1, 2, 3, 4, 5)), List))
    # #     self.assertTrue(isinstance(d.create_child({"a": 1, "b": 2, "c": 3}), Dict))

    # def test_get_by_path(self):
    #     d = Dict(deepcopy(self.data))

    #     self.assertEqual(d["c"], self.data["c"])
    #     self.assertEqual(d["d/e"], self.data["d"]["e"])
    #     self.assertEqual(d["d/f"], self.data["d"]["f"])
    #     self.assertEqual(d["a/0"], self.data["a"][0])
    #     self.assertEqual(d["a/1"], self.data["a"][1])
    #     self.assertEqual(d.get("a/1"), self.data["a"][1])
    #     self.assertEqual(len(d["a"]), 6)

    #     # self.assertListEqual(list(d["a"][2:6]),       [1.0, 2, 3, 4])

    def test_dict_assign(self):
        cache = {}

        d = Dict(cache)

        d["a"] = "hello world {name}!"

        self.assertEqual(cache["a"], "hello world {name}!")

        d["e/f"] = 5

        d["e/g"] = 6

        self.assertEqual(cache["e"]["f"], 5)
        self.assertEqual(cache["e"]["g"], 6)

        d["e/h/0"] = 7

        self.assertEqual(cache["e"]["h"][0], 7)

    def test_list_assign(self):
        cache = []

        d = List(cache)

        d.append("hello world!")

        self.assertEqual(cache[0], "hello world!")

        d.extend([1, 2, 3, 4])

        self.assertEqual(cache[1:], [1, 2, 3, 4])

    def test_update(self):
        d = Dict(
            {
                "a": ["hello world {name}!", "hello world2 {name}!", 1.0, 2, 3, 4],
                "c": "I'm {age}!",
                "d": {"e": "{name} is {age}", "f": "{address}"},
            }
        )

        d.update({"d": {"g": 5}})

        self.assertEqual(d["d"]["e"], "{name} is {age}")
        self.assertEqual(d["d"]["f"], "{address}")
        self.assertEqual(d["d"]["g"], 5)

    def test_insert(self):
        d0 = Dict(
            {
                "a": ["hello world {name}!", "hello world2 {name}!", 1.0, 2, 3, 4],
                "c": "I'm {age}!",
                "d": {"e": "{name} is {age}", "f": "{address}"},
            }
        )

        d0.insert("a", "hello world {name}!")
        d0.update("d", {"g": 5})

        self.assertEqual(d0["d"]["e"], "{name} is {age}")
        self.assertEqual(d0["d"]["f"], "{address}")
        self.assertEqual(d0["d"]["g"], 5)

        d1 = List([])

        d1.insert({"a": [1], "b": 2})

        self.assertEqual(d1[0]["a"][0], 1)
        self.assertEqual(d1[0]["b"], 2)

        # # d1["0/a"].insert(2)

        # self.assertEqual(d1[0]["a"], [1, 2])

    def test_get_by_index(self):
        data = [1, 2, 3, 4, 5]

        d0 = List[int](data)
        # logger.debug(type(d0[0]))
        self.assertIsInstance(d0[0], int)
        self.assertEqual(d0[0], data[0])
        # self.assertListEqual(list(d0[:]), data)

    def test_node_del(self):

        cache = {"a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4]}

        d = Dict(cache)

        del d["a"]

        self.assertTrue(d.get("a", _not_found_) is _not_found_)

    def test_node_insert(self):

        cache = {"this_is_a_cache": True}

        d = Dict[List](cache)

        d.insert("a", "hello world {name}!")

        self.assertEqual(cache["a"][0], "hello world {name}!")

        d.insert("c", 1.23455)

        self.assertEqual(cache["c"][0], 1.23455)
        self.assertEqual(d.get("c/0"), 1.23455)

        d.insert("c", {"a": "hello world", "b": 3.141567})
        self.assertEqual(cache["c"][1]["b"], 3.141567)
        self.assertEqual(d.get("c/1/b"), 3.141567)


# class TestQuery(unittest.TestCase):
#     # fmt:off
#     data = [
#         {"name": "zhangsan",    "age": 18,  "address": "beijing"},
#         {"name": "lisi",        "age": 19,  "address": "shanghai"},
#         {"name": "wangwu",      "age": 20,  "address": "guangzhou"},
#         {"name": "zhaoliu",     "age": 21,  "address": "shenzhen"},
#     ]
#     # fmt:on

#     def test_iter(self):
#         d0 = AoS(deepcopy(self.data), identifier="name")

#         self.assertListEqual([v.__value__ for v in d0], self.data)

#     def test_slice(self):
#         d0 = AoS(deepcopy(self.data), default_value={"genders": "male"})

#         res = d0[1:4].__value__

#         self.assertListEqual(res, self.data[1:4])

#     def test_query(self):
#         d0 = AoS(deepcopy(self.data), identifier="name")
#         res = d0.get("zhangsan")
#         self.assertDictEqual(res, self.data[0])


if __name__ == "__main__":
    unittest.main()
