import typing
from spdm.core.htree import HTree, List
from spdm.utils.tags import _not_found_


class PropertyTree(HTree):
    """属性树，通过 __getattr__ 访问成员，并转换为对应的类型"""

    def __as_node__(self, *args, **kwargs) -> typing.Self | List[typing.Self]:
        node = super().__as_node__(*args, **kwargs)
        if node.__class__ is HTree:
            node = node._entry.get()

        if node is _not_found_:
            pass
        # elif node.__class__ is HTree and node._entry.is_list:
        #     node = List[PropertyTree](node._cache, _entry=node._entry)
        # elif node.__class__ is HTree and node._entry.is_dict:
        #     node.__class__ = PropertyTree
        elif isinstance(node, dict):
            node = PropertyTree(node)
        elif isinstance(node, list) and (len(node) == 0 or any(isinstance(n, dict) for n in node)):
            node = List[PropertyTree](node)

        return node

    def __getattr__(self, key: str) -> typing.Self | List[typing.Self]:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self.__get_node__(key, default_value=_not_found_)

    def __setattr__(self, key: str, value: typing.Any):
        if key.startswith("_"):
            return super().__setattr__(key, value)

        return self.__set_node__(key, value)
