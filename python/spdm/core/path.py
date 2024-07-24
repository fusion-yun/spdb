import ast
import collections.abc
import re
import itertools
import typing
from copy import copy, deepcopy
from enum import Flag, auto
import pathlib
import numpy as np


from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import is_int

from spdm.core.query import Query, as_query


PathLike = str | int | slice | dict | list | Query.tags | None

PathItemLike = str | int | slice | dict | Query.tags

path_like = tuple([int, str, slice, list, tuple, set, dict, Query.tags])


class PathError(Exception):
    def __init__(self, path: typing.List[PathLike], message: str | None = None) -> None:
        if message is None:
            message = f"PathError: {Path(path)}"
        else:
            message = f"PathError: {Path(path)}: {message}"
        super().__init__(message)


class Path(list):
    """Path用于描述数据的路径, 在 HTree ( Hierarchical Tree) 中定位Element, 其语法是 JSONPath 和 XPath的变体，
    并扩展谓词（predicate）语法/查询选择器。

    HTree:
        Hierarchical Tree 半结构化树状数据，树节点具有 list或dict类型，叶节点为 list和dict 之外的primary数据类型，
    包括 int，float,string 和 ndarray。

    基本原则是用python 原生数据类型（例如，list, dict,set,tuple）等

    DELIMITER=`/` or `.`

    | Python 算符          | 字符形式          | 描述
    | ----             |---            | ---
    | N/A              | `$`            | 根对象 （ TODO：Not Implemented ）
    | None             | `@`            | 空选择符，当前对象。当以Path以None为最后一个item时，表示所指元素为leaf节点。
    | `__truediv__`,`__getattr___` | DELIMITER (`/` or `.`)  | 子元素选择符, DELIMITER 可选
    | `__getitem__`         | `[index|slice|selector]`| 数组元素选择符，index为整数,slice，或selector选择器（predicate谓词）

    predicate  谓词, 过滤表达式，用于过滤数组元素.

    | `set`             | `[{a,b,1}]`        | 返回dict, named并集运算符，用于组合多个子元素选择器，并将element作为返回的key， {'a':@[a], 'b':@['b'], 1:@[1] }
    | `list`            | `["a",b,1]`        | 返回list, 并集运算符，用于组合多个子元素选择器，[@[a], @['b'], @[1]]
    | `slice`            | `[start:end:step]`，   | 数组切片运算符, 当前元素为 ndarray 时返回数组切片 @[<slice>]，当前元素为 dict,list 以slice选取返回 list （generator），
    | `slice(None) `        | `*`            | 通配符，匹配任意字段或数组元素，代表所有子节点（children）
    |                | `..`           | 递归下降运算符 (Not Implemented)
    | `dict` `{$eq:4, }`      | `[?(expression)]`     | 谓词（predicate）或过滤表达式，用于过滤数组元素.
    |                | `==、!=、<、<=、>、>=`   | 比较运算符

    Examples

    | Path               | Description
    | ----               | ---
    | `a/b/c`              | 选择a节点的b节点的c节点
    | `a/b/c/1`             | 选择a节点的b节点的c节点的第二个元素
    | `a/b/c[1:3]`           | 选择a节点的b节点的c节点的第二个和第三个元素
    | `a/b/c[1:3:2]`          | 选择a节点的b节点的c节点的第二个和第三个元素
    | `a/b/c[1:3:-1]`          | 选择a节点的b节点的c节点的第三个和第二个元素
    | `a/b/c[d,e,f]`          |
    | `a/b/c[{d,e,f}]          |
    | `a/b/c[{value:{$le:10}}]/value  |
    | `a/b/c.$next/           |

    - 可以迭代器的方式返回多个结果。

    - 可以返回节点（Node）或属性（Attribute）
        - 节点返回类型，为 HTreeNode
        - 属性返回类型，为 PrimaryType

    - 可选择遍历策略(traversal_strategy)，
        - 深度优先(deep-first)，
        - 广度优先(breadth-first)，
        - 前序 (pre-order)，
        - 后序 (post-order)

    - 可对节点进行筛选 filter

    - 可选择遍历范围，
        - 父节点(Parent)，该节点的父节点
        - 子节点（Children），该节点的所有子节点
        - 兄弟(Sibling), 该节点具有相同父节点的所有节点，
        - 祖辈(Ancestor)，从根节点到该节点的路径上的所有节点
        - 子孙(Descendant)，从该节点到任何叶节点的路径上的所有节点
        - 所有子孙(all descendant)，以该节点为根的所有子孙节点

    """

    id_tag_name = "name"
    delimiter = "/"
    # fmt:off
    class tags(Flag):
        # traversal operation 操作
        root  = auto()       # root node    `/`
        parent = auto()      # parent node  `..`
        ancestors =auto()    # 所有祖先节点  `...`
        children = auto()    # 所有子节点    `*`
        descendants = auto() # 所有后代节点  `**`
        slibings=auto()      # 所有兄弟节点  `../*`
    
        current = auto()     # current node
        next  = auto()       # next sibling
        prev  = auto()       # previous sibling

        append = auto()
        extend = auto()
        overwrite  = auto()    # 强制覆盖

    # fmt:on

    def __init__(self, *args):
        super().__init__(Path.parser(*args))

    def __repr__(self):
        return Path._to_str(self)

    def __str__(self):
        return Path._to_str(self)

    def __hash__(self) -> int:
        return self.__str__().__hash__()

    def __copy__(self) -> typing.Self:
        return self.__class__(deepcopy(self[:]))

    def as_url(self) -> str:
        return Path._to_str(self)

    @property
    def is_leaf(self) -> bool:
        return len(self) > 0 and self[-1] is None

    @property
    def is_root(self) -> bool:
        return len(self) == 0

    @property
    def is_regular(self) -> bool:
        return not self.is_generator

    @property
    def is_query(self) -> bool:
        return isinstance(self[-1], Query) if len(self) > 0 else False

    @property
    def is_generator(self) -> bool:
        return any([isinstance(v, (slice, dict)) for v in self])

    @property
    def parent(self) -> typing.Self:
        if len(self) == 0:
            logger.warning("Root node hasn't parents")
            return self
        else:
            return Path(self[:-1])

    @property
    def children(self) -> typing.Self:
        if self.is_leaf:
            raise RuntimeError("Leaf node hasn't child!")
        other = copy(self)
        other.append(slice(None))
        return other

    @property
    def slibings(self):
        return self.parent.children

    @property
    def next(self) -> typing.Self:
        other = copy(self)
        other.append(Path.tags.next)
        return other

    def prepend(self, d) -> typing.Self:
        res = as_path(d)
        return res.append(self)

    def append(self, d) -> typing.Self:
        return Path._resolve(Path._parser_iter(d), self)

    def extend(self, d: list) -> typing.Self:
        return Path._resolve(d, self)

    def with_suffix(self, pth: str) -> typing.Self:
        pth = Path(pth)
        if len(self) == 0:
            return pth
        else:
            res = copy(self)
            if isinstance(res[-1], str) and isinstance(pth[0], str):
                res[-1] += pth[0]
                res.extend(pth[1:])
            else:
                res.extend(pth[:])
        return res

    def __truediv__(self, p) -> typing.Self:
        return copy(self).append(p)

    def __add__(self, p) -> typing.Self:
        return copy(self).append(p)

    def __iadd__(self, p) -> typing.Self:
        return self.append(p)

    def __eq__(self, other) -> bool:
        if isinstance(other, list):
            return super().__eq__(other)
        elif isinstance(other, Path):
            return super().__eq__(other[:])
        else:
            return False

    def collapse(self, idx=None) -> typing.Self:
        """
        - 从路径中删除非字符元素，例如 slice, dict, set, tuple，int。用于从 default_value 中提取数据
        - 从路径中删除指定位置idx: 的元素

        """
        if idx is None:
            return Path([p for p in self if isinstance(p, str)])
        else:
            return Path(self[:idx] + self[idx + 1 :])

    @staticmethod
    def reduce(path: list) -> list:
        if len(path) < 2:
            return path
        elif isinstance(path[0], set) and path[1] in path[0]:
            return Path.reduce(path[1:])
        elif isinstance(path[0], slice) and isinstance(path[1], int):
            start = path[0].start if path[0].start is not None else 0
            step = path[0].step if path[0].step is not None else 1
            stop = start + step * path[1]
            if path[0].stop is not None and stop > path[0].stop:
                raise IndexError(f"index {stop} is out of range")
            return [stop, *Path.reduce(path[2:])]
        else:
            return path

    @staticmethod
    def normalize(p: typing.Any, raw=False) -> typing.Any:
        if p is None:
            res = []
        elif isinstance(p, Path):
            res = p[:]
        elif isinstance(p, str):
            res = Path._parser_str(p)
        elif isinstance(p, (int, slice)):
            res = p
        elif isinstance(p, list):
            res = sum((([v] if not isinstance(v, list) else v) for v in map(Path.normalize, p)), list())
        elif isinstance(p, tuple):
            if len(p) == 1:
                res = Path.normalize(p[0])
            else:
                res = tuple(map(Path.normalize, p))
        elif isinstance(p, collections.abc.Set):
            res = set(map(Path.normalize, p))
        elif isinstance(p, collections.abc.Mapping):
            res = {Path.normalize(k): Path.normalize(v, raw=True) for k, v in p.items()}
        else:
            res = p
            # raise TypeError(f"Path.normalize() only support str or Path, not {type(p)}")

        # if not raw and not isinstance(res, list):
        #   res = [res]

        return res

    @staticmethod
    def _resolve(source, target: list | None = None) -> list:
        """Make the path absolute, resolving all Path.tags (i.e. tag.root, tags.parent)"""
        if target is None:
            target = []

        for p in source:
            if p is Path.tags.parent:
                if len(target) > 0:
                    target.pop()
            elif p is Path.tags.root:
                target.clear()
                list.append(target, Path.tags.root)
            else:
                list.append(target, p)

        return target

    @staticmethod
    def _extend(target: typing.Any):
        if isinstance(target, collections.abc.Generator):
            res = [Path._extend(v) for v in target]
            if len(res) > 1 and isinstance(res[0], tuple) and len(res[0]) == 2:
                res = dict(*res)
            elif len(res) == 1:
                res = res[0]
        else:
            res = target

        return res

    @staticmethod
    def _to_str(p: typing.Any) -> str:
        if isinstance(p, list):
            return Path.delimiter.join([Path._to_str(s) for s in p])
        elif isinstance(p, str):
            return p
        elif isinstance(p, int):
            return str(p)
        elif isinstance(p, tuple):
            m_str = ",".join([Path._to_str(s) for s in p])
            return f"({m_str})"
        elif isinstance(p, set):
            m_str = ",".join([Path._to_str(s) for s in p])
            return f"{{{m_str}}}"
        elif isinstance(p, slice):
            if p.start is None and p.stop is None and p.step is None:
                return "*"
            else:
                return f"{p.start}:{p.stop}:{p.step}"
        elif p is None:
            return ""
        else:
            return str(p)
            # raise NotImplementedError(f"Not support Query,list,mapping,tuple to str,yet! {(p)}")

    # example:
    # a/b_c6/c[{value:{$le:10}}][value]/D/[1，2/3，4，5]/6/7.9.8

    PATH_PATTERN = re.compile(r"(?P<key>[^\[\]\/\,]+)(\[(?P<selector>[^\[\]]+)\])?")

    # 正则表达式解析，匹配一段被 {} 包裹的字符串
    PATH_REGEX_DICT = re.compile(r"\{(?P<selector>[^\{\}]+)\}")

    @staticmethod
    def _parser_selector(s: str | list) -> PathLike:
        if isinstance(s, str):
            s = s.strip(" ")

        if not isinstance(s, str):
            item = s
        elif s.startswith(("[", "(", "{")) and s.endswith(("}", ")", "]")):
            tmp = ast.literal_eval(s)
            if isinstance(tmp, dict):
                item = Query(tmp)  # {Path._parser_str_one(k): d for k, d in tmp.items()}
            elif isinstance(tmp, set):
                item = set([Path._parser_selector(k) for k in tmp])
            elif isinstance(tmp, tuple):
                item = tuple([Path._parser_selector(k) for k in tmp])
            elif isinstance(tmp, list):
                item = [Path._parser_selector(k) for k in tmp]

        elif s.startswith("(") and s.endswith(")"):
            tmp: dict = ast.literal_eval(s)
            item = {Path._parser_selector(k): d for k, d in tmp.items()}
        elif ":" in s:
            tmp = s.split(":")
            if len(tmp) == 2:
                item = slice(int(tmp[0]), int(tmp[1]))
            elif len(tmp) == 3:
                item = slice(int(tmp[0]), int(tmp[1]), int(tmp[2]))
            else:
                raise ValueError(f"Invalid slice {s}")
        elif s == "*":
            item = slice(None)
        elif s == "..":
            item = Path.tags.parent
        elif s == "...":
            item = Path.tags.ancestors
        elif s == "**":
            item = Path.tags.descendants
        elif s == ".":
            item = Path.tags.current
        elif s.isnumeric():
            item = int(s)
        elif s.startswith("$") and hasattr(Path.tags, s[1:]):
            item = Path.tags[s[1:]]
        else:
            item = s

        return item

    @staticmethod
    def _parser_iter(path: typing.Any) -> typing.Generator[PathLike, None, None]:
        if isinstance(path, str):
            if path.startswith("/"):
                yield Path.tags.root
                path = path[1:]
            elif path.isidentifier():
                yield path
                return

            for match in Path.PATH_PATTERN.finditer(path):
                key = match.group("key")

                if key is None:
                    pass

                elif (tmp := is_int(key)) is not False:
                    yield tmp

                elif key == "*":
                    yield Path.tags.children

                elif key == "..":
                    yield Path.tags.parent

                elif key == "...":
                    yield Path.tags.ancestors

                else:
                    yield key

                selector = match.group("selector")
                if selector is not None:
                    yield Path._parser_selector(selector)

        elif isinstance(path, Path.tags):
            yield path

        elif isinstance(path, (int, slice, set, tuple)):
            yield path

        elif isinstance(path, collections.abc.Sequence):
            for item in path:
                yield from Path._parser_iter(item)

        else:
            yield Query(path)

    @staticmethod
    def parser(*args) -> list:
        """Parse the PathLike to list"""
        if len(args) == 1 and (args[0] is None or args[0] is _not_found_):
            return []
        return [*itertools.chain(*map(Path._parser_iter, args))]

    ###########################################################
    # 非幂等
    @typing.final
    def insert(self, target: typing.Any, *args, **kwargs) -> typing.Tuple[typing.Any, typing.Self]:
        """
        根据路径（self）向 target 添加元素。
        当路径指向位置为空时，创建（create）元素
        当路径指向位置为 list 时，追加（ insert ）元素
        当路径指向位置为非 list 时，合并为 [old,new]
        当路径指向位置为 dict, 添加值亦为 dict 时，根据 key 递归执行 insert

        返回修改后的的target和添加元素的路径
        """
        return Path._insert(target, self[:], *args, **kwargs)

    # 幂等
    @typing.final
    def update(self, target: typing.Any, *args, **kwargs) -> typing.Any:
        """
        根据路径（self）更新 target 中的元素。
        当路径指向位置为空时，创建（create）元素
        当路径指向位置为 dict, 添加值亦为 dict 时，根据 key 递归执行 update
        当路径指向位置为空时，用新的值替代（replace）元素

        返回修改后的target
        """
        return Path._update(target, self[:], *args, **kwargs)

    @typing.final
    def delete(self, target: typing.Any, *args, **kwargs) -> None:
        """根据路径（self）删除 target 中的元素。
        成功返回 True，否则为 False
        """
        return Path._delete(target, self[:], *args, **kwargs)

    @typing.final
    def find(self, target, *p_args, **p_kwargs) -> typing.Any:
        """返回第一个search结果，若没有则返回 default_value
        p_args,p_kwargs: project 参数, p_args[0] 为 project 操作符
        """
        return Path._find(target, self[:], *p_args, **p_kwargs)

    @typing.final
    def search(self, target, *p_args, **p_kwargs) -> typing.Generator[typing.Any, None, None]:
        """遍历路径（self）中的元素，返回元素的索引和值"""
        yield from Path._search(target, self[:], *p_args, **p_kwargs)

    # ----------------------------------------------------------------------------------

    @typing.final
    def put(self, target: typing.Any, value, **kwargs) -> typing.Any:
        """put value to target, alias of update"""
        return self.update(target, value, **kwargs)

    @typing.final
    def get(self, target: typing.Any, default_value: typing.Any = _not_found_):
        """get value from source, alias of find"""
        return self.find(target, default_value=default_value)

    @typing.final
    def pop(self, target, default_value: typing.Any = _not_found_):
        """get and delete value from target"""
        value = self.get(target, default_value=_not_found_)
        if value is _not_found_:
            value = default_value
        else:
            self.delete(self)
        return value

    @typing.final
    def query(self, target, *p_args, **p_kwargs) -> typing.Any:
        """alias of find"""
        return self.find(target, *p_args, **p_kwargs)

    ###########################################################

    @staticmethod
    def _set(target, key, *args, **kwargs):
        """set values to target[key] and return target[key]"""
        if len(kwargs) > 0:
            args = (*args, kwargs)
            kwargs = {}

        for value in args:
            if value is _not_found_ or value is target:
                pass
            elif hasattr(target.__class__, "__set_node__"):
                target.__set_node__(key, value)
            elif key is None and not isinstance(value, (dict)):
                target = value
            elif target is _not_found_:
                if key is None:
                    target = value
                elif isinstance(key, int):
                    target = [_not_found_] * (key) + [value]
                elif isinstance(key, slice):
                    target = [_not_found_] * (key.stop) + [value]
                elif isinstance(key, str):
                    target = {key: value}
                elif key in (Path.tags.append, Path.tags.extend):
                    target = value
                else:
                    raise KeyError(f"{(target)} is not indexable! key={key} ")
            elif isinstance(target, collections.abc.MutableSequence):
                if key is None:
                    target = value
                elif isinstance(key, int):
                    if len(target) < key + 1:
                        target.extend([_not_found_] * (key + 1 - len(target)))
                    target[key] = value
                elif isinstance(key, slice):
                    if len(target) < key.stop + 1:
                        target.extend([_not_found_] * (key.stop + 1 - len(target)))
                    target[key] = value
                elif key is Path.tags.append:
                    target.append(value)
                elif key is Path.tags.extend:
                    target.extend(value)
                elif isinstance(key, (str, dict)):
                    query = as_query(key)
                    for idx, node in enumerate(target):
                        if not query.check(node):
                            continue
                        new_node = Path._update(node, [], value)
                        if new_node is not node:
                            target[idx] = new_node

                else:
                    raise KeyError(f"{type(target)} is not indexable! key={key} ")
            elif isinstance(target, collections.abc.MutableMapping):
                if key is Path.tags.append:
                    target = [target, value]
                elif isinstance(key, (str, int)):
                    obj = target.get(key, _not_found_)
                    target[key] = Path._update(obj, [], value)
                elif key is None:
                    if isinstance(value, collections.abc.Mapping):
                        for k, v in value.items():
                            target = Path(k).update(target, v)
                    else:
                        target = value
                else:
                    raise KeyError(f"{type(target)} is not indexable! key={key} value={value}")
            elif key is Path.tags.append:
                target = [target, value]
            elif key is Path.tags.extend:
                target = [target] + value
            else:
                target = value

        return target

    @staticmethod
    def _get(target, key, *args, **kwargs):
        if target is _not_found_ or target is None:
            res = target
        elif key is None:
            res = target
        elif key is Path.tags.parent:
            res = getattr(target, "_parent", _not_found_)
        elif key is Path.tags.current:
            res = target
        # elif isinstance(key, (tuple, list)):
        #     res = [Path._get(source, k, *args, **kwargs) for k in key]
        # elif isinstance(key, set):  # mapping
        #     res = {k: Path._get(source, k, *args, **kwargs) for k in key}
        # elif isinstance(key, dict):  # mapping
        #     res = {k: Path._get(source, v, *args, **kwargs) for k, v in key.items()}
        elif isinstance(key, str) and key.isidentifier() and hasattr(target.__class__, key):
            res = getattr(target, key, _not_found_)
        elif hasattr(target.__class__, "__get_node__") and not (isinstance(key, str) and key.startswith("_")):
            res = target.__get_node__(key, *args, **kwargs)
            args = tuple()
            kwargs = {}
        elif isinstance(target, collections.abc.Mapping):
            res = target.get(key, _not_found_)
        elif isinstance(target, collections.abc.Sequence) and isinstance(key, int):
            if key >= len(target):
                res = _not_found_
            else:
                res = target[key]
        elif isinstance(target, collections.abc.Sequence) and isinstance(key, tuple):
            res = target[*key]
        elif isinstance(target, collections.abc.Sequence) and isinstance(key, slice):
            res = target[key]
        elif isinstance(target, collections.abc.Sequence) and isinstance(key, (str)):
            query = as_query(name=key)
            try:
                res = next(filter(query.check, target))
            except StopIteration:
                res = _not_found_
        elif isinstance(target, collections.abc.Sequence) and isinstance(key, Query):
            query = as_query(key)
            res = [*filter(query.check, target)]
        elif isinstance(target, object) and isinstance(key, str) and key.isidentifier():
            res = getattr(target, key, _not_found_)
        elif isinstance(target, np.ndarray) and isinstance(key, (int, slice)):
            res = target[key]
        else:
            raise KeyError(f"Can not get '{key}' from '{type(target)}' ")

        res = Path._project(res, *args, **kwargs)
        return res

    @staticmethod
    def _insert(target, path: typing.List[PathItemLike], *args, **kwargs):
        return Path._update(target, path + [Path.tags.append], *args, **kwargs)

    @staticmethod
    def _update(target, path: typing.List[PathItemLike], *args, **kwargs):

        if path is None or len(path) == 0:
            key = None
            sub_path = []
        else:
            key = path[0]
            sub_path = path[1:]

        if key is None:
            if len(sub_path) == 0:
                target = Path._set(target, None, *args, **kwargs)
            else:
                target = Path._update(target, sub_path, *args, **kwargs)

        elif key is Path.tags.parent:
            target = Path._update(getattr(target, "_parent", _not_found_), sub_path, *args, **kwargs)

        elif key is Path.tags.current:
            target = Path._update(target, sub_path, *args, **kwargs)

        elif key in (Path.tags.append, Path.tags.extend):
            target = Path._set(target, key, Path._update(_not_found_, sub_path, *args, **kwargs))

        elif isinstance(key, (set, tuple)):
            for k in key:
                target = Path._update(target, Path(k)[:] + sub_path, *args, **kwargs)

        elif isinstance(key, dict):
            if not (len(args) == 1 and len(kwargs) == 0):
                raise RuntimeError("only accept one argument, when key is dict")
            source = args[0]
            for k, v in key.items():
                target = Path._update(target, Path(k)[:] + sub_path, Path._get(source, Path(v)[:] + sub_path))

        elif isinstance(key, Query) or key in (
            Path.tags.children,
            Path.tags.ancestors,
            Path.tags.descendants,
            Path.tags.slibings,
        ):
            for node in Path._search(target, [key]):  #  "Traversal update {path}"
                Path._update(node, sub_path, *args, **kwargs)

        else:
            old_node = Path._get(target, key)
            new_node = Path._update(old_node, sub_path, *args, **kwargs)
            target = Path._set(target, key, new_node)

        return target

    @staticmethod
    def _delete(target: typing.Any, path: typing.List[PathItemLike], *args, **kwargs) -> None:
        if len(args) + len(kwargs) > 0:
            raise NotImplementedError((args, kwargs))

        if target is _not_found_ or len(path) == 0:
            return

        parent = Path._find(target, path[:-1])
        key = path[-1]
        if parent is _not_found_:
            pass
        elif hasattr(parent.__class__, "__del_node__"):
            parent.__del_node__(key)
        elif isinstance(parent, collections.abc.Mapping) and isinstance(key, str):
            if key in parent:
                del parent[key]

        elif isinstance(parent, collections.abc.MutableSequence) and isinstance(key, int):
            if key < len(parent):
                del parent[key]

        else:
            raise KeyError(f"{key}")

    @staticmethod
    def _project(target: typing.Any, *p_args, **p_kwargs):
        """
        TODO: 更多操作，例如，排序，过滤，分组，聚合等
        """

        if len(p_args) == 0:
            return target if target is not _not_found_ else p_kwargs.get("default_value", _not_found_)

        projection = p_args[0]
        p_args = p_args[1:]

        if isinstance(projection, Query.tags):
            projection = getattr(Query, f"_op_{projection.name}", projection)

        if callable(projection):
            try:
                res = projection(target, **p_kwargs)
            except Exception as error:
                raise RuntimeError(f'Fail to call "{projection}"!  ') from error

        elif projection is Query.tags.get_value:
            res = Path._project(target, *p_args, **p_kwargs)

        elif isinstance(projection, tuple):
            res = (Path._project(target, k, *p_args, **p_kwargs) for k in projection)

        elif isinstance(projection, list):
            res = [Path._project(target, k, *p_args, **p_kwargs) for k in projection]

        elif isinstance(projection, set):
            res = {k: Path._project(target, k, *p_args, **p_kwargs) for k in projection}

        elif isinstance(projection, dict):
            res = {k: Path._project(target, v, *p_args, **p_kwargs) for k, v in projection.items()}

        elif projection is _not_found_ and target is _not_found_:
            res = p_kwargs.get("default_value", _not_found_)

        else:
            res = Path._update(target, [], projection)

        return res

    @staticmethod
    def _find(target, path: typing.List[PathItemLike], *p_args, **p_kwargs):

        key = path[0] if len(path) > 0 else _not_found_

        sub_path = path[1:]

        if key is _not_found_:
            value = Path._project(target, *p_args, **p_kwargs)
        elif key is None:
            value = Path._find(target, sub_path, *p_args, **p_kwargs)
        elif isinstance(key, (int, str)):
            value = Path._find(Path._get(target, key), sub_path, *p_args, **p_kwargs)
        elif isinstance(key, tuple):
            if isinstance(target, np.ndarray):
                value = Path._find(target[*key], sub_path, *p_args, **p_kwargs)
            else:
                value = [Path._find(target, Path(k)[:] + sub_path) for k in key]
                value = tuple(value)
            value = Path._project(value, *p_args, **p_kwargs)
        elif isinstance(key, list):
            value = [Path._find(target, Path(k)[:] + sub_path) for k in key]
            value = Path._project(value, *p_args, **p_kwargs)
        elif isinstance(key, set):
            value = {k: Path._find(target, Path(k)[:] + sub_path) for k in key}
            value = Path._project(value, *p_args, **p_kwargs)
        elif isinstance(key, dict):
            value = {k: Path._find(target, Path(v)[:] + sub_path) for k, v in key.items()}
            value = Path._project(value, *p_args, **p_kwargs)
        elif key is Path.tags.parent:
            value = Path._find(getattr(target, "_parent", _not_found_), sub_path, *p_args, **p_kwargs)
        elif key is Path.tags.current:
            value = Path._find(target, sub_path, *p_args, **p_kwargs)
        elif key is Path.tags.ancestors:
            obj = target
            value = _not_found_

            while obj is not _not_found_ and obj is not None:
                value = Path._find(obj, sub_path, default_value=_not_found_)
                if value is not _not_found_:
                    break
                obj = getattr(obj, "_parent", _not_found_)
            value = Path._project(value, *p_args, **p_kwargs)
        elif isinstance(key, Query):
            try:
                obj = next(Path._search(target, [key]))
            except StopIteration:
                obj = _not_found_
            value = Path._find(obj, sub_path, *p_args, **p_kwargs)
        elif len(sub_path) == 0:
            value = Path._get(target, key)
            value = Path._project(value, *p_args, **p_kwargs)
        else:
            raise KeyError(f"Cannot index {target} by {key}!")

        return value

    @staticmethod
    def _search(
        target, path: typing.List[PathItemLike], *p_args, **p_kwargs
    ) -> typing.Generator[typing.Any, None, None]:
        """遍历。
        @NOTE:
            - 叶节点无输出
            - Sequence: 输出 value 子节点
            - Mapping:  输出 key和 value
        @FIXME:
            - level 参数，用于实现多层遍历，尚未实现
        """
        if target is _not_found_ or target is None:
            yield path, Path._project(target, *p_args, **p_kwargs)

        elif path is None or len(path) == 0:

            if hasattr(target.__class__, "__search__"):
                yield from target.__search__(*p_args, **p_kwargs)

            elif len(p_args) > 0 and p_args[0] is Query.tags.get_key:
                if isinstance(target, collections.abc.Mapping):
                    yield from map(lambda k: Path._project(k, *p_args[1:], **p_kwargs), target.keys())

                elif isinstance(target, collections.abc.Iterable) and not isinstance(target, str):
                    yield from map(lambda v: Path._project(v, *p_args[1:], **p_kwargs), range(len(target)))

                else:
                    yield Path._project(0, *p_args[1:], **p_kwargs)
            elif len(p_args) > 0 and p_args[0] is Query.tags.get_item:
                if isinstance(target, collections.abc.Mapping):
                    yield from map(lambda kv: Path._project(kv, *p_args[1:], **p_kwargs), target.items())

                elif isinstance(target, collections.abc.Iterable) and not isinstance(target, str):
                    yield from map(lambda kv: Path._project(kv, *p_args[1:], **p_kwargs), enumerate(target))

                else:
                    yield 0, Path._project(target, *p_args[1:], **p_kwargs)

            else:
                if len(p_args) > 0 and p_args[0] is Query.tags.get_value:
                    p_args = p_args[1:]

                if isinstance(target, collections.abc.Mapping):
                    yield from map(lambda v: Path._project(v, *p_args, **p_kwargs), target.values())

                elif isinstance(target, collections.abc.Iterable) and not isinstance(target, str):
                    yield from map(lambda v: Path._project(v, *p_args, **p_kwargs), target)

                else:
                    yield Path._project(target, *p_args, **p_kwargs)

        else:

            key = path[0]
            sub_path = path[1:]

            if key in (None, Path.tags.current):
                yield from Path._search(target, sub_path, *p_args, **p_kwargs)

            elif key is Path.tags.ancestors:
                obj = target
                while obj is not _not_found_:
                    obj = Path._get(obj, Path.tags.parent)
                    if obj is _not_found_:
                        break
                    yield from Path._search(obj, sub_path, *p_args, **p_kwargs)
            elif key is Path.tags.children:
                if hasattr(target.__class__, "children"):
                    for obj in target.children():
                        res = Path._search(obj, sub_path, *p_args, **p_kwargs)
                        if isinstance(res, collections.abc.Iterable):
                            yield from res
                        else:
                            yield res
                elif isinstance(target, collections.abc.Sequence) and not isinstance(target, str):
                    for obj in target:
                        yield from Path._search(obj, sub_path, *p_args, **p_kwargs)
                elif isinstance(target, collections.abc.Mapping):
                    for v in target.values():
                        yield from Path._search(v, sub_path, *p_args, **p_kwargs)

            elif key is Path.tags.slibings:
                parent = Path._find(target, Path.tags.parent)
                for child in Path._search(parent, Path.tags.children):
                    if child is target:
                        continue
                    yield from Path._search(child, sub_path, *p_args, **p_kwargs)

            elif key is Path.tags.descendants:
                for child in Path._search(target, Path.tags.children):
                    yield from Path._search(child, sub_path, *p_args, **p_kwargs)
                    yield from Path._search(child, [Path.tags.children] + sub_path, *p_args, **p_kwargs)

            elif isinstance(key, (str, int)):
                yield from Path._search(Path._get(target, key), sub_path, *p_args, **p_kwargs)

            else:
                raise KeyError(f"Can not search {target} by {key}")


_T = typing.TypeVar("_T")


def update_tree(target: _T, *args, **kwargs) -> _T:
    return Path().update(target, *args, **kwargs)


def merge_tree(*args, **kwargs) -> _T:
    return update_tree({}, *args, **kwargs)


def as_path(*args):
    if len(args) == 0:
        return Path()
    path = args[0]
    args = args[1:]
    if isinstance(path, Path):
        return path

    if isinstance(path, pathlib.Path):
        path = path.as_posix()

    return Path(path, *args)
