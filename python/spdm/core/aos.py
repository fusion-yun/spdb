
import collections.abc
import typing
from copy import deepcopy


from spdm.core.entry import Entry
from spdm.core.htree import HTree, List, HTreeNode
from spdm.core.path import Path, as_path

from spdm.utils.tags import _not_found_, _undefined_

_T = typing.TypeVar("_T")


class AoS(List[_T]):
    """
    Array of structure

    FIXME: 需要优化！！
        - 数据结构应为 named list or ordered dict
        - 可以自动转换 list 类型 cache 和 entry
    """

    def __missing__(self, key) -> _T:
        tag = f"@{Path.id_tag_name}"

        if self._cache is not None and len(self._cache) > 0:
            pass
        elif self._entry is not None:
            keys = set([key for key in self._entry.child(f"*/{tag}").for_each()])
            self._cache = [{tag: key} for key in keys]
        else:
            self._cache = []

        value = deepcopy(self._metadata.get("default_initial_value", _not_found_) or {})

        value[f"@{Path.id_tag_name}"] = key

        # self._cache.append(value)

        return value

    def __get_node__(self, key, default_value=_undefined_, **kwargs) -> _T:
        """AoS._find_ 当键值不存在时，默认强制调用 __missing__"""
        self._sync_cache()
        if default_value is _not_found_:
            default_value = _undefined_

        return super().__get_node__(key, default_value=default_value, **kwargs)

    def _sync_cache(self):
        if len(self._cache) == 0 and self._entry is not None:
            keys = self._entry.child(f"*/@{Path.id_tag_name}").get()
            if isinstance(keys, collections.abc.Sequence):
                keys = set([k for k in keys if k is not _not_found_ and k is not None])
                self._cache = [{f"@{Path.id_tag_name}": k} for k in keys]

    def __search__(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int | str, HTreeNode], None, None]:
        self._sync_cache()
        tag = f"@{Path.id_tag_name}"
        if len(self._cache) > 0:
            for idx, v in enumerate(self._cache):
                if isinstance(v, (dict, HTree)) and (key := Path(tag).get(v, _not_found_)) is not _not_found_:
                    yield idx, self.__get_node__(key, *args, **kwargs)
                else:
                    yield idx, self.__get_node__(idx, *args, **kwargs)
        elif self._entry is not None:
            for idx, e in self._entry.search():
                if isinstance(e, Entry):
                    yield idx, self.__get_node__(idx, _entry=e)
                else:
                    yield idx, self.__get_node__(idx, default_value=e, _entry=self._entry.child(idx))

        # if self._entry is None:
        #     _entry = None
        # elif key is _not_found_ or v is None:
        #     _entry = self._entry.child(idx)
        # else:
        #     _entry = self._entry.child({tag: key})
        # yield self._type_convert(v, idx, _entry=_entry)

    # def fetch(self, *args, _parent=_not_found_, **kwargs) -> typing.Self:
    #     return self.__duplicate__([HTreeNode._do_fetch(obj, *args, **kwargs) for obj in self], _parent=_parent)

    # def dump(self, entry: Entry, **kwargs) -> None:
    #     """将数据写入 entry"""
    #     entry.insert([{}] * len(self._cache))
    #     for idx, value in enumerate(self._cache):
    #         if isinstance(value, HTree):
    #             value.dump(entry.child(idx), **kwargs)
    #         else:
    #             entry.child(idx).insert(value)
