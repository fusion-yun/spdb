import unittest
from spdm.core.pluggable import Pluggable


class Dummy(Pluggable):
    _plugin_registry = {}


class TestPluggable(unittest.TestCase):
    def test_regisiter(self):
        class Foo(Dummy, plugin_name="foo"):
            pass

        self.assertIs(Dummy._plugin_registry.get(f"{self.__module__}.foo", None), Foo)

        Dummy.register("foo0", Foo)
        self.assertIs(Dummy._plugin_registry.get(f"{self.__module__}.foo0", None), Foo)

    def test_decorator(self):

        @Dummy.register(plugin_name="foo1")
        class Foo1(Dummy):
            pass

        self.assertIs(Dummy._plugin_registry.get(f"{self.__module__}.foo1", None), Foo1)

    def test_create(self):
        class Goo(Dummy, plugin_name="goo"):
            pass

        # self.assertIsInstance(Dummy("goo"), Goo)
        self.assertIsInstance(Dummy(plugin_name="goo"), Goo)
        # self.assertIsInstance(Dummy({"plugin_name": "goo"}), Goo)
        # self.assertIsInstance(Dummy({"plugin_name": "boo"}, plugin_name="goo"), Goo)


if __name__ == "__main__":
    unittest.main()
