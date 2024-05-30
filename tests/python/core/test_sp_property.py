import unittest

import numpy as np
from spdm.core.htree import AoS, Dict, List
from spdm.core.sp_property import SpTree, sp_property
from spdm.core.time_series import TimeSeriesAoS
from spdm.utils.logger import logger


class Foo(SpTree):
    a: float = sp_property(default_value=4)
    b: float = sp_property()
    c: float = sp_property()


class Goo(SpTree):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    value: float = sp_property()

    foos: List[Foo] = sp_property(default_value={"a": 1, "b": 2, "c": 3})


class Doo(SpTree):

    foo: Foo = sp_property(default_value={"a": 1})

    goo: Goo = sp_property(default_value={"value": 3.14})

    foo_list: List[Foo] = sp_property()

    balaaa = sp_property[Foo](default={"bala": 1})


eq_data = {
    "time": [0.0],
    "vacuum_toroidal_field": {"r0": 6.2, "b0": [-5.3]},
    "code": {"name":  "eq_analyze", },
    "$default_value": {
        "time_slice": {
            "profiles_2d": {"grid": {"dim1": 129, "dim2": 257}},
            "boundary": {"psi_norm": 0.99},
            "coordinate_system": {"grid": {"dim1": 256, "dim2": 128}}
        }}
}


class Mesh(SpTree):
    dim1: int = sp_property()
    dim2: int = sp_property()


class EquilibriumProfiles2d(SpTree):

    grid: Mesh = sp_property()


class EqTimeSlice(SpTree):

    profiles_2d: AoS[EquilibriumProfiles2d] = sp_property()


class Eq(SpTree):

    time: np.ndarray = sp_property()
    time_slice: TimeSeriesAoS[EqTimeSlice] = sp_property()


class TestSpProperty(unittest.TestCase):
    def test_get(self):
        cache = {"foo": {"a": 1234}, }
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

        cache = {"foo_list": [{"a": 1234}, {"b": 1234}, {"c": 1234}, ]}

        d = Doo(cache)

        self.assertFalse(isinstance(cache["foo_list"], Foo))
        self.assertTrue(isinstance(d.foo_list, List))
        # self.assertTrue(isinstance(cache["foo_list"], List))
        self.assertTrue(isinstance(d.foo_list[0], Foo))

        self.assertEqual(d.foo_list[0]["a"], 1234)

    def test_set(self):
        cache = {"foo": {"a": 1234}}
        d = Doo(cache)
        self.assertEqual(cache["foo"]["a"], 1234)
        d.foo.a = 45678.0
        self.assertEqual(d._cache["foo"].a, 45678)

    def test_delete(self):
        cache = {"foo": {"a": 1234}}
        d = Doo(cache)
        self.assertEqual(cache["foo"]["a"], 1234)
        del d.foo
        self.assertTrue("foo" not in cache)

    def test_list_default_child_value(self):
        cache = [{"a": 6}, {"a": 7}, {"a": 8}, {}]
        d = AoS[Foo](cache, default_value={"a": 1, "b": 2, "c": 3})
        self.assertEqual(d[0].a, 6)
        self.assertEqual(d[0].b, 2)
        self.assertEqual(d[0].c, 3)
        self.assertEqual(d[-1].a, 4)
        self.assertEqual(d[-1].b, 2)
        self.assertEqual(d[-1].c, 3)

    def test_sp_data(self):

        eq = Eq(eq_data)

        self.assertTrue(isinstance(eq.time_slice, TimeSeriesAoS))

        self.assertEqual(eq.time_slice[0].profiles_2d[0].grid.dim1,
                         eq_data["$default_value"]["time_slice"]["profiles_2d"]["grid"]["dim1"])


if __name__ == '__main__':
    unittest.main()
