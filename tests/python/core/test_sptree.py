import unittest
import typing
import numpy as np
from spdm.core.htree import List, Dict
from spdm.core.sp_tree import SpTree, sp_property, Dataclass

from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger


class Foo(SpTree):
    a: float = 4
    b: float
    c: float


class Goo(SpTree):
    value: float
    foos: List[Foo] = {"a": 1, "b": 2, "c": 3}


class Doo(SpTree):

    doo: int = sp_property(strict=True)

    foo: Foo

    goo: Goo = {"value": 3.14}

    foo_list: List[Foo]

    balaaa: Foo = {"bala": 1}


eq_data = {
    "time": [0.0],
    "vacuum_toroidal_field": {"r0": 6.2, "b0": [-5.3]},
    "code": {
        "name": "eq_analyze",
    },
    "time_slice": [
        {
            "profiles_2d": {"grid": {"dim1": 129, "dim2": 257}},
            "boundary": {"psi_norm": 0.99},
            "coordinate_system": {"grid": {"dim1": 256, "dim2": 128}},
        }
    ],
}


class Mesh(SpTree):
    dim1: int = 1
    dim2: int = 1


class EquilibriumProfiles2d(SpTree):

    grid: Mesh


class EqTimeSlice(SpTree):

    profiles_2d: EquilibriumProfiles2d


class Eq(SpTree):
    time: np.ndarray
    time_slice: List[EqTimeSlice]


class TestSpTree(unittest.TestCase):

    def test_get(self):
        cache = {"foo": {"a": 1234}}
        d = Doo(cache)

        self.assertFalse(isinstance(cache["foo"], Foo))
        self.assertTrue(isinstance(d.foo, Foo))
        self.assertTrue(isinstance(d._cache["foo"], Foo))

        self.assertTrue(isinstance(d.balaaa, Foo))
        self.assertTrue(isinstance(d._cache["balaaa"], Foo))

        self.assertEqual(d.foo.a, d._cache["foo"].a)

    def test_default_value(self):

        d = Doo()
        self.assertEqual(d.goo.value, 3.14)
        self.assertEqual(d._cache["goo"].value, 3.14)

    def test_get_list(self):
        cache = {
            "foo_list": [
                {"a": 1234},
                {"b": 1234},
                {"c": 1234},
            ]
        }

        d = Doo(cache)

        self.assertFalse(isinstance(cache["foo_list"], Foo))
        self.assertTrue(isinstance(d.foo_list, List))
        # self.assertTrue(isinstance(cache["foo_list"], List))
        self.assertEqual(d.foo_list[0].__class__, Foo)

        self.assertEqual(d.foo_list[0]["a"], 1234)

    def test_set(self):
        cache = {"foo": {"a": 1234}}
        d = Doo(cache)
        self.assertEqual(cache["foo"]["a"], 1234)
        d.foo.a = 45678.0
        self.assertEqual(d["foo"].a, 45678)

    def test_delete(self):
        cache = {"doo": 1234}
        d = Doo(cache)
        self.assertEqual(d.doo, 1234)
        del d.doo
        self.assertEqual(d._cache["doo"], _not_found_)
        with self.assertRaises(AttributeError):
            d.doo

    def test_sp_data(self):

        eq = Eq(eq_data)

        self.assertTrue(isinstance(eq.time_slice, List))
        self.assertTrue(isinstance(eq.time_slice[0], EqTimeSlice))
        time_slice: EqTimeSlice = eq.time_slice[0]
        profiles_2d: EquilibriumProfiles2d = time_slice.profiles_2d
        self.assertEqual(
            profiles_2d.grid.dim1,
            eq_data["time_slice"][0]["profiles_2d"]["grid"]["dim1"],
        )

    def test_list_default_child_value(self):
        cache = [{"a": 6}, {"b": 7}, {"c": 8}, _not_found_]

        class Boo(SpTree, default_value={"a": 1, "b": 2, "c": 3}):
            a: int
            b: int
            c: float

        d = List[Boo](cache)

        self.assertEqual(d[0].a, 6)
        self.assertEqual(d[0].b, 2)
        self.assertEqual(d[0].c, 3)
        self.assertEqual(d[1].a, 1)
        self.assertEqual(d[1].b, 7)
        self.assertEqual(d[1].c, 3)
        self.assertEqual(d[-1].a, 1)
        self.assertEqual(d[-1].b, 2)
        self.assertEqual(d[-1].c, 3)

    def test_dataclass(self):

        class Foo1(Dataclass):
            x: float
            y: float
            z: float = 0.1

        foo0 = Foo1(1, 2)
        self.assertEqual(foo0.x, 1)
        self.assertEqual(foo0.y, 2)
        self.assertEqual(foo0.z, 0.1)
        # self.assertEqual(foo0._metadata.get("name", None), "Foo1")

        foo2 = Foo1(2, 3, 4)
        self.assertEqual(foo2.x, 2)
        self.assertEqual(foo2.y, 3)
        self.assertEqual(foo2.z, 4)


if __name__ == "__main__":
    unittest.main()
