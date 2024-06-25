import typing
import unittest


from spdm.core.generic_helper import GenericHelper


class TestGeneric(unittest.TestCase):
    def test_specification(self):
        _T0 = typing.TypeVar("_T0")
        _T1 = typing.TypeVar("_T1")
        _T2 = typing.TypeVar("_T2")
        _S0 = typing.TypeVar("_S0")
        _S1 = typing.TypeVar("_S1")
        _S2 = typing.TypeVar("_S2")
        _Ts = typing.TypeVarTuple("_Ts")

        class Foo(GenericHelper[_T0, _T1, _T2]):
            TValue = _T2
            goo: _T0
            boo: _T1 = 10
            koo: typing.Tuple[_T1, _T2]

            def func(self, a: _T0, b: _T2) -> _T1:
                pass

        class Boo(Foo[int, _S1, _T2]):
            pass

        self.assertEqual(Boo[str, float].TValue, float)

        self.assertDictEqual(
            typing.get_type_hints(Boo),
            {
                "goo": int,
                "boo": _S1,
                "koo": typing.Tuple[_S1, _T2],
            },
        )
        self.assertDictEqual(
            typing.get_type_hints(Boo[str, float]),
            {
                "goo": int,
                "boo": str,
                "koo": typing.Tuple[str, float],
            },
        )
        self.assertDictEqual(
            typing.get_type_hints(Boo[int, str].func),
            {
                "a": int,
                "b": float,
                "return": str,
            },
        )

    def test_inheritance(self):
        _T0 = typing.TypeVar("_T0")
        _T1 = typing.TypeVar("_T1")
        _T2 = typing.TypeVar("_T2")
        _S0 = typing.TypeVar("_S0")
        _S1 = typing.TypeVar("_S1")
        _S2 = typing.TypeVar("_S2")

        class Foo(GenericHelper[_T0, _T1, _T2]):
            TValue = _T2
            foo: _T0
            boo: _T1 = 10
            koo: typing.Tuple[_T1, _T2]

            def func(self, a: _T0, b: _T2) -> _T1:
                pass

        class Goo(GenericHelper[_T0, _T1, _T2]):
            GType = _T2
            goo: _T0
            koo: typing.Tuple[_T1, _T2]

            def func(self, a: _T0, b: _T2) -> _T1:
                pass

        class Boo(Foo[int, _S1, _T2], Goo[int, _T0, _T2]):
            BooType1: _S1 = 5
            BooType2: _T0

        class Aoo(Boo[_T0, _T1, _T2]):
            AooType: _T2

        tp = Aoo[complex, str, float]

        self.assertEqual(tp.boo, 10)

        self.assertDictEqual(
            typing.get_type_hints(tp),
            {
                "goo": int,
                "koo": typing.Tuple[complex, str],
                "foo": int,
                "boo": complex,
                "BooType1": complex,
                "BooType2": float,
                "AooType": float,
            },
        )


if __name__ == "__main__":
    unittest.main()
