import pprint
import typing
import unittest
from copy import deepcopy

from spdm.core.htree import Dict, HTree, List, HTreeNode
from spdm.utils.logger import logger
from spdm.utils.tags import _undefined_
from spdm.utils.typing import as_value


class Foo(Dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
    def test_empty_node(self):
        n = HTreeNode()

        self.assertTrue(n.__empty__())
        self.assertFalse(n.__null__())
        self.assertEqual(len(n) == 0)

    def test_null_node(self):
        n = HTreeNode(None)

        self.assertFalse(n.__empty__())
        self.assertTrue(n.__null__())
        self.assertEqual(len(n) == 0)

    data = {
        "a": ["hello world {name}!", "hello world2 {name}!", 1, 2, 3, 4],
        "c": "I'm {age}!",
        "d": {"e": "{name} is {age}", "f": "{address}"},
    }

    # def test_new(self):
    #     self.assertTrue(isinstance(HTree("hello"), HTree))
    #     self.assertTrue(isinstance(HTree(1), HTree))
    #     self.assertTrue(isinstance(HTree(np.ones([10, 20])), HTree))
    #     self.assertTrue(isinstance(HTree([1, 2, 3, 4, 5]), List))
    #     self.assertTrue(isinstance(HTree((1, 2, 3, 4, 5)), List))
    #     self.assertTrue(isinstance(HTree({"a": 1, "b": 2, "c": 3}), Dict))
    #     # self.assertFalse(isinstance(HTree({1, 2, 3, 4, 5}), List))

    # def test_create(self):
    #     cache = []
    #     d = HTree(cache)
    #     self.assertEqual(d.create_child("hello"), "hello")
    #     self.assertEqual(d.create_child(1), 1)
    #     v = np.ones([10, 20])
    #     self.assertIs(d.create_child(v), v)
    #     self.assertTrue(isinstance(d.create_child("hello", always_node=True), Node))

    #     self.assertTrue(isinstance(d.create_child([1, 2, 3, 4, 5]), List))
    #     self.assertTrue(isinstance(d.create_child((1, 2, 3, 4, 5)), List))
    #     self.assertTrue(isinstance(d.create_child({"a": 1, "b": 2, "c": 3}), Dict))

    def test_get_by_path(self):
        d = Dict(deepcopy(self.data))

        self.assertEqual(d["c"]._value_, self.data["c"])
        self.assertEqual(d["d/e"]._value_, self.data["d"]["e"])
        self.assertEqual(d["d/f"]._value_, self.data["d"]["f"])
        self.assertEqual(d["a/0"]._value_, self.data["a"][0])
        self.assertEqual(d["a/1"]._value_, self.data["a"][1])
        self.assertEqual(d.get("a/1"), self.data["a"][1])
        self.assertEqual(len(d["a"]), 6)

        # self.assertListEqual(list(d["a"][2:6]),       [1.0, 2, 3, 4])

    def test_assign(self):
        cache = {}

        d = Dict(cache)

        d["a"] = "hello world {name}!"

        self.assertEqual(cache["a"], "hello world {name}!")
        d["e"] = {}
        d["e"]["f"] = 5
        d["e"]["g"] = 6

        self.assertEqual(cache["e"]["f"].__value__, 5)
        self.assertEqual(cache["e"]["g"].__value__, 6)

    def test_update(self):
        d = Dict(deepcopy(test_data))

        d._update_({"d": {"g": 5}})

        self.assertEqual(d["d"]["e"]._value_, "{name} is {age}")
        self.assertEqual(d["d"]["f"]._value_, "{address}")
        self.assertEqual(d["d"]["g"]._value_, 5)

    def test_insert(self):
        d0 = Dict(deepcopy(test_data))

        d0._insert_({"a": "hello world {name}!"})
        d0._update_({"d": {"g": 5}})

        self.assertEqual(d0["d"]["e"]._value_, "{name} is {age}")
        self.assertEqual(d0["d"]["f"]._value_, "{address}")
        self.assertEqual(d0["d"]["g"]._value_, 5)

        d1 = List([])

        d1._insert_({"a": [1], "b": 2})

        self.assertEqual(d1[0]["a"][0]._value_, 1)
        self.assertEqual(d1[0]["b"]._value_, 2)

        d1["0/a"].insert(2)

        self.assertEqual(d1[0]["a"]._value_, [1, 2])

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

        self.assertTrue(cache["a"], _undefined_)

    def test_node_insert(self):
        d = Dict[List]({"this_is_a_cache": True})

        d["a"] = "hello world {name}!"
        self.assertEqual(d["a"]._value_, "hello world {name}!")

        d["c"]._insert_(1.23455)
        d["c"]._insert_({"a": "hello world", "b": 3.141567})

        self.assertEqual(d["c"][0]._value_, 1.23455)
        self.assertEqual(d.get("c/0"), 1.23455)
        self.assertEqual(d["c"][1]["b"]._value_, 3.141567)
        self.assertEqual(d.get("c/1/b"), 3.141567)

    def test_type_hint(self):
        d1 = List[HTree]([])
        d1._insert_({"a": 1, "b": 2})

        self.assertIsInstance(d1[0], HTree)

        self.assertEqual(len(d1), 1)
        self.assertEqual(d1[0]["a"]._value_, 1)
        self.assertEqual(d1[0]["b"]._value_, 2)

        data = [1, 2, 3, 4, 5]

        class Foo:
            def __init__(self, v, **kwargs) -> None:
                self.v = v

        d1 = List[Foo](deepcopy(data))

        self.assertIsInstance(d1[2], Foo)
        self.assertEqual(d1[2].v, data[2])


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
