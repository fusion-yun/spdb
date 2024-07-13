import unittest
import typing
from spdm.utils.tags import _not_found_
from spdm.core.entry import open_entry
from spdm.core.file import File


class TestFile(unittest.TestCase):
    def test_plugin(self):

        class Doo(File, plugin_name=["doo", "do"]):

            def read(self, *args, **kwargs) -> typing.Any:
                return kwargs

            def write(self, *args, **kwargs) -> None:
                return None

        self.assertIsInstance(open_entry("/a/b/c.do"), Doo.Entry)
        self.assertIsInstance(open_entry("file+doo:///a/b/c"), Doo.Entry)


if __name__ == "__main__":
    unittest.main()
