import unittest
from copy import deepcopy

from spdm.core.path import Path
from spdm.core.pluggable import Pluggable

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
import typing


class TBase(Pluggable):
    _registry = {}

    @classmethod
    def _guess_plugin_name(cls, cls_name, *args, **kwargs) -> typing.List[str]:
        return [cls_name]

 

@TBase.register("A")
class MyClassA:
    def my_method(self):
        print("Method called from MyClassA")


@TBase.register("B")
class MyClassB:
    def my_method(self):
        print("Method called from MyClassB")


class TestPlugin(unittest.TestCase):

    def test_create(self):
        foo = TBase("A")
        self.assertTrue(isinstance(foo, MyClassA))


if __name__ == '__main__':
    unittest.main()
