import unittest
from copy import deepcopy
import typing

from spdm.core.path import Path
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import get_origin, get_args, isinstance_generic


class TestTyping(unittest.TestCase):

    def test_get_origin(self):
        _T = typing.TypeVar("_T")

        class Foo(typing.Generic[_T]):
            pass

        foo = Foo[int]()

        self.assertEqual(get_origin(int), int)
        self.assertEqual(get_origin(Foo), Foo)
        self.assertEqual(get_origin(Foo[int]), Foo)

        class Goo(Foo[_T]):
            pass

        self.assertEqual(get_origin(Goo), Goo)
        self.assertEqual(get_origin(Goo[int]), Goo)

        class Doo(Foo[float]):
            pass

        self.assertEqual(get_origin(Doo), Doo)

        self.assertEqual(get_origin(1.234), float)
        self.assertEqual(get_origin(Foo()), Foo)
        self.assertEqual(get_origin(Foo[int]()), Foo)
        self.assertEqual(get_origin(Goo[int]()), Goo)
        self.assertEqual(get_origin(Doo()), Doo)

    # def test_get_args(self):
    #     _T = typing.TypeVar("_T")

    #     class Foo(typing.Generic[_T]):
    #         pass

    #     self.assertEqual(get_args(int), tuple())
    #     self.assertEqual(get_args(Foo), tuple())
    #     self.assertEqual(get_args(Foo[int]), (int,))

    #     class Goo(Foo[_T]):
    #         pass

    #     self.assertEqual(get_args(Goo), tuple())
    #     self.assertEqual(get_args(Goo[int])[0], int)

    #     class Doo(Foo[float]):
    #         pass

    #     self.assertEqual(get_args(Doo), (float,))

    def test_isinstance_generic(self):
        _T = typing.TypeVar("_T")

        class Foo(list, typing.Generic[_T]):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            pass

        foo = Foo[int]()

        self.assertTrue(isinstance_generic(foo, Foo[int]))
        self.assertTrue(isinstance_generic(foo, list))
        self.assertTrue(isinstance_generic(foo, Foo))

        self.assertFalse(isinstance_generic(foo, Foo[float]))
        self.assertFalse(isinstance_generic(foo, dict))

        goo = Foo()
        self.assertTrue(isinstance_generic(goo, Foo))
        self.assertTrue(isinstance_generic(goo, Foo[float]))


if __name__ == "__main__":
    unittest.main()
