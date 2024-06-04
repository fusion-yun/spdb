from __future__ import annotations
import collections.abc
import functools
import typing
from copy import deepcopy

from typing_extensions import Self


from .entry import Entry
from .htree import HTree, List, Dict, HTreeNode
from .path import Path, PathLike, as_path, OpTags, update_tree, merge_tree

from ..utils.tags import _not_found_, _undefined_
from ..utils.typing import array_type, get_args, get_type_hint
from ..utils.logger import logger

_T = typing.TypeVar("_T")


class QueryResult(HTree):
    """Handle the result of query"""

    def __init__(self, query: PathLike, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._path = as_path(query)

    def __getattr__(self, name: str):
        return self._get(name)

    def _get(self, query: str | int | slice | dict, *args, **kwargs):
        default_value = kwargs.pop("default_value", _not_found_)
        _VT = get_args(self.__orig_class__)[0]
        if isinstance(query, str):
            if default_value is _not_found_ and isinstance(self._default_value, dict):
                default_value = self._default_value.get(query, _not_found_)
            tp = get_type_hint(_VT, query)

            return QueryResult[tp](self._path.append(query), *args, default_value=default_value, **kwargs)
        else:
            return QueryResult[_VT](self._path.append(query), *args, default_value=default_value, **kwargs)

    @property
    def _value_(self) -> typing.Any:
        value = super()._query(self._path)
        if isinstance(value, list):
            value = functools.reduce(self._default_reducer, value)
        return value

    def __call__(self, *args, **kwargs) -> typing.Any:
        value = super()._query(self._path, op=Path.tags.call, *args, **kwargs)

        if isinstance(value, list):
            value = functools.reduce(self._default_reducer, value)

        return value

    @staticmethod
    def _default_reducer(first: typing.Any, second: typing.Any) -> typing.Any:
        if first is _not_found_:
            return second
        elif second is _not_found_ or second is None:
            return second
        elif isinstance(first, (str)):
            return first
        elif isinstance(first, array_type) and isinstance(second, array_type):
            return first + second
        elif isinstance(first, (dict, list)) or isinstance(second, (dict, list)):
            return update_tree(first, second)
        else:
            return first + second

    def children(self) -> typing.Generator[_T | HTree, None, None]:
        """遍历 children"""
        cache = self._cache if self._cache is not _not_found_ else self._default_value

        if not isinstance(cache, list) or len(cache) == 0:
            yield from super().children()

        else:
            for idx, value in enumerate(cache):
                if isinstance(value, (dict, Dict)):
                    id = value.get(self._identifier, None)
                else:
                    id = None
                if id is not None:
                    entry = self._entry.child({f"@{self._identifier}": id})
                else:
                    entry = None

                yield self._type_convert(value, idx, entry=entry)


_TTree = typing.TypeVar("_TTree")


class AoS(List[_TTree]):
    """
    Array of structure

    FIXME: 需要优化！！
        - 数据结构应为 named list or ordered dict
        - 可以自动转换 list 类型 cache 和 entry
    """

    def __missing__(self, key) -> _TTree:
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

    def _find_(self, key, *args, default_value=_undefined_, **kwargs) -> _TTree:
        """AoS._find_ 当键值不存在时，默认强制调用 __missing__"""
        self._sync_cache()
        if default_value is _not_found_:
            default_value = _undefined_

        return super()._find_(key, *args, default_value=default_value, **kwargs)

    def _update_(self, key, value, op=None, *args, **kwargs) -> Self:
        if (key is None or key is _not_found_) and op is not Path.tags.extend:
            key = as_path(f"@{Path.id_tag_name}").get(value, None)

            if key is _not_found_ or key is None:
                raise KeyError(f"key is not found in {value} {op}")

        super()._update_(key, value, op, *args, **kwargs)

        return self

    def _sync_cache(self):
        if len(self._cache) == 0 and self._entry is not None:
            keys = self._entry.child(f"*/@{Path.id_tag_name}").get()
            if isinstance(keys, collections.abc.Sequence):
                keys = set([k for k in keys if k is not _not_found_ and k is not None])
                self._cache = [{f"@{Path.id_tag_name}": k} for k in keys]

    def _for_each_(self, *args, **kwargs) -> typing.Generator[typing.Tuple[int | str, HTreeNode], None, None]:
        self._sync_cache()
        tag = f"@{Path.id_tag_name}"
        if len(self._cache) > 0:
            for idx, v in enumerate(self._cache):
                if isinstance(v, (dict, HTree)) and (key := Path(tag).get(v, _not_found_)) is not _not_found_:
                    yield idx, self._find_(key, *args, **kwargs)
                else:
                    yield idx, self._find_(idx, *args, **kwargs)
        elif self._entry is not None:
            for idx, e in self._entry.for_each():
                if isinstance(e, Entry):
                    yield idx, self._type_convert(_not_found_, idx, _entry=e)
                else:
                    yield idx, self._type_convert(e, idx, _entry=self._entry.child(idx))

        # if self._entry is None:
        #     _entry = None
        # elif key is _not_found_ or v is None:
        #     _entry = self._entry.child(idx)
        # else:
        #     _entry = self._entry.child({tag: key})
        # yield self._type_convert(v, idx, _entry=_entry)

    def fetch(self, *args, _parent=_not_found_, **kwargs) -> Self:
        return self.__duplicate__([HTreeNode._do_fetch(obj, *args, **kwargs) for obj in self], _parent=_parent)

    def dump(self, entry: Entry, **kwargs) -> None:
        """将数据写入 entry"""
        entry.insert([{}] * len(self._cache))
        for idx, value in enumerate(self._cache):
            if isinstance(value, HTree):
                value.dump(entry.child(idx), **kwargs)
            else:
                entry.child(idx).insert(value)
