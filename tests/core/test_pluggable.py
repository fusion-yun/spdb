import unittest
from spdm.core.pluggable import Pluggable


class Dummy(Pluggable, plugin_prefix="dummy."):
    _plugin_registry = {}


class TestPluggable(unittest.TestCase):
    def test_regisiter(self):
        class Foo(Dummy, plugin_name="foo"):
            pass

        self.assertIs(Dummy._plugin_registry.get("dummy.foo", None), Foo)

        Dummy.register("foo0", Foo)
        self.assertIs(Dummy._plugin_registry.get("dummy.foo0", None), Foo)

    def test_decorator(self):

        @Dummy.register(plugin_name="foo1")
        class Foo1(Dummy):
            pass

        self.assertIs(Dummy._plugin_registry.get("dummy.foo1", None), Foo1)

    def test_create(self):
        class Goo(Dummy, plugin_name="goo"):
            pass

        self.assertIsInstance(Dummy(_plugin_name="goo"), Goo)


if __name__ == "__main__":
    unittest.main()
