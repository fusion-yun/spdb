from __future__ import annotations

import ast
import collections.abc
import inspect
import pprint
import re
import typing
from copy import copy, deepcopy
from enum import Flag, auto

import numpy as np

from spdm.utils.logger import deprecated, logger
from spdm.utils.misc import serialize
from spdm.utils.tags import _not_found_, _undefined_
from spdm.utils.type_hint import array_type, isinstance_generic, is_int, is_tree


# fmt:off
class OpTags(Flag):
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
 
    # CRUD 
    query  = auto()      # Read/Query/GET
    update = auto()      # Update/PUT
    insert = auto()      # Insert/Create/POST
    delete = auto()      # DELETE


    append = auto()
    extend = auto()
    overwrite  = auto()    # 强制覆盖
    
 

    call  = auto()      # call function
    exists = auto()
    is_leaf = auto()
    is_list=auto()
    is_dict=auto()
    check_type = auto() # check type
    get_key=auto()         # 返回键值
    get_value=auto()         # 返回键值
    search = auto()     # search by query return idx
    dump  = auto()      # rescurive get all data

    # for sequence
    reduce = auto()
    sort  = auto()

    # predicate 谓词
    check  = auto()
    count  = auto()

    # boolean
    equal  = auto()
    le   = auto()
    ge   = auto()
    less  = auto()
    greater = auto()
# fmt:on


QueryLike = dict | OpTags | None


class Query:
    def __init__(self, query: QueryLike = None, only_first=True, **kwargs) -> None:
        if query is _not_found_ or query is None:
            query = {}
        if isinstance(query, Query):
            self._query = Query._parser(query._query, **kwargs)
        else:
            self._query = Query._parser(query, **kwargs)

        self._only_first = only_first

    def __str__(self) -> str:
        p = self._query

        if not isinstance(p, dict):
            return str(p)
        else:
            m_str = ",".join([f"{k}:{Path._to_str(v)}" for k, v in p.items()])
            return f"?{{{m_str}}}"

    @classmethod
    def _parser(cls, query: QueryLike, **kwargs) -> dict:
        if query is None:
            query = {".": Path._op_fetch}

        elif isinstance(query, Path.tags):
            query = {".": f"${query.name}"}

        elif isinstance(query, str) and query.startswith("$"):
            query = {".": query}

        elif isinstance(query, str):
            query = {f"@{Path.id_tag_name}": query}

        elif isinstance(query, dict):
            query = {k: Query._parser(v) for k, v in query.items()}

        else:
            raise TypeError(f"{(query)}")

        if isinstance(query, dict):
            return update_tree(query, kwargs)

        else:
            return query

    def __call__(self, target, *args, **kwargs) -> typing.Any:
        return self.check(target, *args, **kwargs)

    @staticmethod
    def _eval_one(target, k, v) -> typing.Any:
        res = False
        if k == "." or k is OpTags.current:
            res = Query._q_equal(target, v)

        elif isinstance(k, str) and k.startswith("@"):
            if hasattr(target.__class__, k[1:]):
                res = Query._q_equal(getattr(target, k[1:], _not_found_), v)

            elif isinstance(target, collections.abc.Mapping):
                res = Query._q_equal(target.get(k, _not_found_), v)

        return res

    def _eval(self, target) -> bool:
        return all([Query._eval_one(target, k, v) for k, v in self._query.items()])

    def check(self, target) -> bool:
        res = self._eval(target)

        if isinstance(res, list):
            return all(res)
        else:
            return bool(res)

    def find_next(self, target, start: int | None, **kwargs) -> typing.Tuple[typing.Any, int | None]:
        next = start
        return _not_found_, next

    @staticmethod
    def _q_equal(target, value) -> bool:
        if isinstance(target, collections.abc.Sequence):
            return value in target
        else:
            return target == value

    # fmt: off
    _q_neg         =np.negative   
    _q_add         =np.add     
    _q_sub         =np.subtract   
    _q_mul         =np.multiply   
    _q_matmul      =np.matmul    
    _q_truediv     =np.true_divide 
    _q_pow         =np.power    
    _q_equal       =np.equal    
    _q_ne          =np.not_equal  
    _q_lt          =np.less     
    _q_le          =np.less_equal  
    _q_gt          =np.greater   
    _q_ge          =np.greater_equal
    _q_radd        =np.add     
    _q_rsub        =np.subtract   
    _q_rmul        =np.multiply   
    _q_rmatmul     =np.matmul    
    _q_rtruediv    =np.divide    
    _q_rpow        =np.power    
    _q_abs         =np.abs     
    _q_pos         =np.positive   
    _q_invert      =np.invert    
    _q_and         =np.bitwise_and 
    _q_or          =np.bitwise_or  
    _q_xor         =np.bitwise_xor 
    _q_rand        =np.bitwise_and 
    _q_ror         =np.bitwise_or  
    _q_rxor        =np.bitwise_xor 
    _q_rshift      =np.right_shift 
    _q_lshift      =np.left_shift  
    _q_rrshift     =np.right_shift 
    _q_rlshift     =np.left_shift  
    _q_mod         =np.mod     
    _q_rmod        =np.mod     
    _q_floordiv    =np.floor_divide 
    _q_rfloordiv_  =np.floor_divide 
    _q_trunc       =np.trunc    
    _q_round       =np.round    
    _q_floor       =np.floor    
    _q_ceil        =np.ceil     
    # fmt: on


def as_query(query: QueryLike = None, **kwargs) -> Query | slice:
    if isinstance(query, slice):
        return query
    elif isinstance(query, Query):
        return query
    else:
        return Query(query, **kwargs)


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
    tags = OpTags

    def __init__(self, *args, **kwargs):
        super().__init__(args[0] if len(args) == 1 and isinstance(args[0], list) else Path.parser(args), **kwargs)

    def __repr__(self):
        return Path._to_str(self)

    def __str__(self):
        return Path._to_str(self)

    def __hash__(self) -> int:
        return self.__str__().__hash__()

    def __copy__(self) -> Path:
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
    def parent(self) -> Path:
        if len(self) == 0:
            logger.warning("Root node hasn't parents")
            return self
        else:
            return Path(self[:-1])

    @property
    def children(self) -> Path:
        if self.is_leaf:
            raise RuntimeError("Leaf node hasn't child!")
        other = copy(self)
        other.append(slice(None))
        return other

    @property
    def slibings(self):
        return self.parent.children

    @property
    def next(self) -> Path:
        other = copy(self)
        other.append(Path.tags.next)
        return other

    def prepend(self, d) -> Path:
        res = as_path(d)
        return res.append(self)

    def append(self, d) -> Path:
        return Path._resolve(Path._parser_iter(d), self)

    def extend(self, d: list) -> Path:
        return Path._resolve(d, self)

    def with_suffix(self, pth: str) -> Path:
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

    def __truediv__(self, p) -> Path:
        return copy(self).append(p)

    def __add__(self, p) -> Path:
        return copy(self).append(p)

    def __iadd__(self, p) -> Path:
        return self.append(p)

    def __eq__(self, other) -> bool:
        if isinstance(other, list):
            return super().__eq__(other)
        elif isinstance(other, Path):
            return super().__eq__(other[:])
        else:
            return False

    def collapse(self, idx=None) -> Path:
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
    def _expand(target: typing.Any):
        if isinstance(target, collections.abc.Generator):
            res = [Path._expand(v) for v in target]
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

        elif isinstance(path, (int, slice, set)):
            yield path

        elif isinstance(path, collections.abc.Sequence):
            for item in path:
                yield from Path._parser_iter(item)

        else:
            yield Query(path)

    @staticmethod
    def parser(path) -> list:
        """Parse the PathLike to list"""
        return [*Path._parser_iter(path)]

    ###########################################################
    # 非幂等
    @typing.final
    def insert(self, target: typing.Any, value, **kwargs) -> typing.Tuple[_T, Path]:
        """
        根据路径（self）向 target 添加元素。
        当路径指向位置为空时，创建（create）元素
        当路径指向位置为 list 时，追加（ insert ）元素
        当路径指向位置为非 list 时，合并为 [old,new]
        当路径指向位置为 dict, 添加值亦为 dict 时，根据 key 递归执行 insert

        返回修改后的的target和添加元素的路径
        """
        return Path._insert(target, self[:], value, **kwargs)

    # 幂等
    @typing.final
    def update(self, target: typing.Any, value, **kwargs) -> typing.Any:
        """
        根据路径（self）更新 target 中的元素。
        当路径指向位置为空时，创建（create）元素
        当路径指向位置为 dict, 添加值亦为 dict 时，根据 key 递归执行 update
        当路径指向位置为空时，用新的值替代（replace）元素

        返回修改后的target
        """
        return Path._update(target, self[:], value, **kwargs)

    @typing.final
    def delete(self, target: typing.Any) -> bool:
        """根据路径（self）删除 target 中的元素。
        成功返回 True，否则为 False
        """
        return Path._delete(target, self[:])

    @typing.final
    def search(self, target, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
        """遍历路径（self）中的元素，返回元素的索引和值"""
        yield from Path._search(target, self[:], *args, **kwargs)

    # alias
    @typing.final
    def query(self, *args, **kwargs) -> typing.Any:
        """返回第一个search结果，失败则报错"""
        try:
            value = next(self.search(*args, **kwargs))
        except StopIteration as error:
            logger.error(f"Fail to query {str(self)}", exc_info=error)
        else:
            return value
        return next(self.search(*args, **kwargs))

    @typing.final
    def find(self, *args, default_value=_not_found_, **kwargs) -> typing.Any:
        """返回第一个search结果，若没有则返回 default_value"""
        try:
            value = next(self.search(*args, **kwargs))
        except StopIteration:
            return default_value
        else:
            return value

    @typing.final
    def put(self, target: typing.Any, *args, **kwargs) -> typing.Any:
        """put value to target, alias of update"""
        return self.update(target, *args, **kwargs)

    @typing.final
    def get(self, target: typing.Any, **kwargs):
        """get value from source, alias of find"""
        return self.find(target, **kwargs)

    @typing.final
    def pop(self, target, default_value=_not_found_, **kwargs):
        """get and delete value from target"""
        value = self.get(target, default_value=_not_found_, **kwargs)
        if value is not _not_found_:
            self.delete(self)
            return value
        else:
            return default_value

    def copy(self, source: typing.Any, target: typing.Any = None, **kwargs):
        """copy object to target"""
        return self.do_copy(source, target, self[:], **kwargs)

    ###########################################################

    @staticmethod
    def _set(obj, key, *args, **kwargs):
        """set values to target[key] and return target[key]"""
        if hasattr(obj.__class__, "__set_node__"):
            obj.__set_node__(key, *args, **kwargs)
            return obj

        if isinstance(key, int):
            if obj is _not_found_:
                obj = [_not_found_] * (key + 1)
            elif isinstance(obj, collections.abc.MutableSequence) and len(obj) <= key - 1:
                obj.extend([_not_found_] * (key + 1 - len(obj)))
            else:
                raise TypeError(f"{type(obj)} is not indexable!")
        elif obj is _not_found_ and isinstance(key, str):
            obj = {}

        for value in (*args, kwargs):
            if value is _not_found_:
                pass
            elif obj is _not_found_:
                obj = value

            elif isinstance(value, collections.abc.Mapping):
                for k, v in value.items():
                    obj = Path._update(obj, [k], v)
            else:
                obj = value

        return obj

    @staticmethod
    def _get(obj, key):
        if hasattr(obj.__class__, "__get_node__"):
            res = obj.__get_node__(key)

        elif isinstance(obj, collections.abc.Mapping):
            res = obj.get(key, _not_found_)

        elif isinstance(obj, collections.abc.Sequence) and not isinstance(obj, str):
            if key >= len(obj):
                raise IndexError(f"Index out of range {key}>={len(obj)}!")

            res = obj[key]

        elif isinstance(key, str) and key.isidentifier():
            res = getattr(obj, key, _not_found_)

        else:
            raise KeyError(f"Can not get {key} from {type(obj)}")

        return res

    @staticmethod
    def _insert(target, path: typing.List[PathItemLike], *args, **kwargs):
        return Path._update(target, path + [Path.tags.append], *args, **kwargs)

    @staticmethod
    def _update(target, path: typing.List[PathItemLike], *args, **kwargs):

        path = [0] + path
        holder = [target]
        current_ = holder

        for idx, key in enumerate(path):
            if key in (Path.tags.children, Path.tags.ancestors, Path.tags.descendants, Path.tags.slibings):
                # for p in Path._search(current_, path[idx + 1 :]):
                #     Path._update(current_, p, *args, **kwargs)
                # break
                # raise NotImplementedError("Traversal update")
                break
            elif key is Path.tags.current:
                next_ = current_
                key = None
            elif key is Path.tags.parent:
                next_ = getattr(current_, "_parent", _not_found_)
                key = None
            elif isinstance(key, (int, str)):
                next_ = Path._get(current_, key)
            else:
                raise NotImplementedError(f"Update {path[1:idx+1]}")

            tmp = next_
            if idx == len(path) - 1:
                if hasattr(next_.__class__, "__set_node__"):
                    next_.__set_node__(*args, **kwargs)
                else:
                    for value in (*args, kwargs):
                        if value is _not_found_:
                            pass
                        elif next_ is _not_found_:
                            next_ = value

                        elif isinstance(value, collections.abc.Mapping):
                            for k, v in value.items():
                                next_ = Path._update(next_, [k], v)
                        else:
                            next_ = value

            elif isinstance(path[idx + 1], int):
                if isinstance(next_, collections.abc.MutableSequence) :
                    if  path[idx + 1] >= len(next_):
                        next_.extend([_not_found_] * (path[idx + 1] + 1 - len(next_)))
                elif next_ is _not_found_:
                    next_ = [[_not_found_] * (path[idx + 1] + 1)]

            elif next_ is _not_found_:
                next_ = {}

            if next_ is tmp:
                pass
            elif key is not None:
                Path._set(current_, key, next_)
            else:
                raise RuntimeError(f"key is None! {path[1:idx+1]}")
            
            current_ = next_
  
        return holder[0]

    @staticmethod
    def _delete(target: typing.Any, path: typing.List[PathItemLike], **kwargs) -> typing.Any:
        if value is _undefined_ and len(args) == 0:
            return target
        if path is None:
            path = []
        elif not isinstance(path, list):
            path = [path]

        if len(args) > 0:
            _op = args[0]
            args = args[1:]
        else:
            _op = None

        if len(path) == 0 and target is value:
            pass

        elif len(path) == 0:
            if target is value:
                pass

            elif value is _not_found_ and _op is None:
                pass

            elif _op is Path.tags.overwrite or target is _not_found_:
                target = value

            elif hasattr(target.__class__, "_update_"):
                target._update_([], value, _op, *args, **kwargs)

            elif isinstance(value, dict) and (_op is None or _op is Path.tags.update):
                for k, v in value.items():
                    target = Path._delete(target, as_path(k)[:], v, _op, *args, **kwargs)

            elif _op is None:
                target = value

            elif _op is Path.tags.insert or _op is Path.tags.append:
                if isinstance(target, collections.abc.MutableSequence) and not isinstance(target, str):
                    target.append(value)
                else:
                    target = [target, value]

            elif _op is Path.tags.extend:
                if target is _not_found_:
                    target = value

                elif (
                    isinstance(target, collections.abc.MutableSequence)
                    and not isinstance(target, str)
                    and isinstance(value, list)
                ):
                    target.extend(value)
                else:
                    target = [target, value]

            else:
                raise NotImplementedError(f" {_op} {target} {value}")
                target = Path._project(_op, target, value, *args, **kwargs)

        else:
            if target is _not_found_:
                if isinstance(path[0], str):
                    target = {}
                else:
                    target = []

            obj = target

            path_length = len(path)

            idx = 0

            while idx < path_length:
                key = path[idx]

                if not is_tree(obj):
                    raise TypeError(f" {obj} is not a Tree! key= {key} idx={idx} path={path}")

                elif key is Path.tags.current or key is None:
                    pass

                elif key is Path.tags.parent:
                    obj = getattr(obj, "_parent", _not_found_)

                elif key is Path.tags.children:
                    if hasattr(obj.__class__, "for_each"):
                        for k, v in enumerate(obj.for_each()):
                            old_value = v
                            new_value = Path._delete(old_value, path[idx + 1 :], _op, **kwargs)
                            if new_value is not old_value:
                                obj[k] = new_value

                    elif isinstance(obj, collections.abc.MutableMapping):
                        for k, v in obj.items():
                            old_value = v
                            new_value = Path._delete(old_value, path[idx + 1 :], _op, **kwargs)
                            if new_value is not old_value:
                                obj[k] = new_value

                    elif isinstance(obj, collections.abc.MutableSequence):
                        for k, v in enumerate(obj):
                            old_value = v
                            new_value = Path._delete(old_value, path[idx + 1 :], _op, **kwargs)
                            if new_value is not old_value:
                                obj[k] = new_value

                    else:
                        raise KeyError(f"{type(obj)} has not children!")

                    break

                elif isinstance(key, Path.tags):
                    raise NotImplementedError(key)

                elif hasattr(obj.__class__, "_update_"):
                    # FIXME：更改好的实现，但需要 debug
                    if idx == path_length - 1:
                        obj._update_(key, value, _op, *args, **kwargs)
                    else:
                        obj._update_(key, _not_found_ if not isinstance(path[idx + 1], str) else {}, _idempotent=_op)

                    obj = obj._find_(key, default_value=_not_found_)
                    # old_value = obj._find_(key, default_value=_not_found_)

                    # if is_tree(old_value) and idx < path_length - 1:
                    #     new_value = old_value
                    # elif idx == path_length - 1:
                    #     new_value = Path._do_update(old_value, [], value, _idempotent=_idempotent, **kwargs)
                    # else:
                    #     new_value = Path._do_update(old_value, path[idx + 1], _not_found_, _idempotent=_idempotent)
                    #     idx -= 1

                    # if old_value is not new_value:
                    #     obj = obj._update_(key, new_value)
                    # else:
                    #     obj = new_value

                elif isinstance(key, str) and key.isidentifier() and hasattr(obj.__class__, key):
                    old_value = getattr(obj, key, _not_found_)

                    if is_tree(old_value) and idx < path_length - 1:
                        new_value = old_value
                    elif idx == path_length - 1:
                        new_value = Path._delete(old_value, [], value, _op, **kwargs)
                    else:
                        new_value = Path._delete(old_value, path[idx + 1], _not_found_, _op)
                        idx -= 1

                    if old_value is _not_found_ or old_value is not new_value:
                        setattr(obj, key, new_value)
                        obj = getattr(obj, key)
                    else:
                        obj = new_value

                elif isinstance(obj, collections.abc.MutableMapping):
                    old_value = obj.get(key, _not_found_)

                    if is_tree(old_value) and idx < path_length - 1:
                        new_value = old_value
                    elif idx == path_length - 1:
                        new_value = Path._delete(old_value, [], value, _op, *args, **kwargs)
                    else:
                        new_value = Path._delete(old_value, path[idx + 1], _not_found_, _op)

                    if old_value is _not_found_ or old_value is not new_value:
                        obj[key] = new_value
                        obj = obj[key]
                    else:
                        obj = new_value

                elif isinstance(obj, collections.abc.MutableSequence) and isinstance(key, (Path.tags, slice)):
                    for v in obj[key]:
                        Path._delete(v, path[idx + 1 :], value, **kwargs)
                    break

                elif isinstance(obj, collections.abc.MutableSequence):
                    if key is None:
                        key = len(obj)

                    if isinstance(key, int):
                        if key >= (len(obj)):
                            obj.extend([_not_found_] * (key - len(obj) + 1))

                        old_value = obj[key]

                        if is_tree(old_value) and idx < path_length - 1:
                            new_value = old_value
                        elif idx == path_length - 1:
                            new_value = Path._delete(old_value, [], value, _op, **kwargs)
                        else:
                            new_value = Path._delete(old_value, path[idx + 1], _not_found_, _op)

                    elif isinstance(key, str):
                        query = Query(key)
                        for jdx, old_value in enumerate(obj):
                            if query.check(old_value):
                                path[idx] = key = jdx
                                break
                        else:
                            old_value = {f"@{Path.id_tag_name}": key}
                            path[idx] = key = len(obj)
                            obj.append(old_value)
                            _op = None

                        if is_tree(old_value) and idx < path_length - 1:
                            new_value = old_value
                        elif idx == path_length - 1:
                            new_value = Path._delete(old_value, [], value, _op, **kwargs)
                        else:
                            raise ValueError(f"Unknown value {old_value}")

                    elif isinstance(obj, collections.abc.MutableSequence) and isinstance(key, Query):
                        query = key
                        for key, old_value in enumerate(obj):
                            if query.check(old_value):
                                path[idx] = key
                                break
                        else:
                            raise KeyError(f"Can not update {obj} at {key}!")

                        if is_tree(old_value) and idx < path_length - 1:
                            new_value = old_value
                        elif idx == path_length - 1:
                            new_value = Path._delete(old_value, [], value, _op, **kwargs)
                        elif old_value is _not_found_:
                            new_value = Path._delete({f"@{Path.id_tag_name}": key}, path[idx + 1], _not_found_, _op)
                        else:
                            raise ValueError(f"Unknown value {old_value}")

                    if old_value is _not_found_ or old_value is not new_value:
                        obj[key] = new_value
                        obj = obj[key]

                    else:
                        obj = new_value

                else:
                    raise KeyError(f"Can not find {key} in {obj}!")

                idx += 1

        return target

    @staticmethod
    def _search_(
        target, path: typing.List[PathItemLike], projection=None, **kwargs
    ) -> typing.Generator[typing.Any, None, None]:
        """遍历容器子节点。
        @NOTE:
            - 叶节点无输出
            - Sequence: 输出 value 子节点
            - Mapping:  输出 key和 value
        @FIXME:
            - level 参数，用于实现多层遍历，尚未实现
        """
        obj = target
        for idx, p in enumerate(path):
            if obj is _not_found_:
                break
            if isinstance(p, (str, int)):
                pass
            else:
                match p:
                    case Path.tags.parent:
                        obj = getattr(obj, "_parent", _not_found_)

            if p is Path.tags.children:
                target = Path._search(target, path[:idx])
                suffix = path[idx + 1 :]
                break
            elif isinstance(p, Path.tags):
                raise NotImplementedError(p)
        else:
            target = Path._search(target, path)
            suffix = []

        if isinstance(target, collections.abc.Sequence) and not isinstance(target, str):
            for k, v in enumerate(target):
                yield k, Path._search(v, suffix, **kwargs)

        elif isinstance(target, collections.abc.Mapping):
            for k, v in target.items():
                yield k, Path._search(v, suffix, **kwargs)

        elif target is not _not_found_:
            logger.warning(f"{type(target)} is not iterable!")

    @staticmethod
    def _search(
        target: typing.Any, path: typing.List[PathItemLike], **kwargs
    ) -> typing.Generator[typing.Any, None, None]:

        obj = target

        for idx, key in enumerate(path):
            if obj is _not_found_:
                break

            elif key is None or key is Path.tags.current or obj is _not_found_ or obj is None:
                pass

            elif (
                isinstance(key, str)
                and key.isidentifier()
                and (attr := getattr(obj, key, _not_found_)) is not _not_found_
            ):
                obj = attr

            elif len(path) > 1 and path[1] is Path.tags.next:
                if isinstance(key, int):
                    new_key = key + 1
                else:
                    raise NotImplementedError(f"{type(obj)} {path}")

                res = Path._search(obj, [new_key] + path[idx + 2 :], *args, **kwargs)

            elif len(path) > 1 and path[1] is Path.tags.prev:
                if isinstance(key, int):
                    new_key = key - 1
                else:
                    raise NotImplementedError(f"{type(obj)} {path}")

                res = Path._search(obj, [new_key] + path[idx + 2 :], **kwargs)

            elif isinstance(key, Path.tags):
                match key:
                    case Path.tags.parent:
                        obj = getattr(obj, "_parent", _not_found_)

                    case Path.tags.ancestors:
                        # 逐级查找上层 _parent, 直到找到
                        while obj is not None and obj is not _not_found_:
                            if not isinstance(obj, collections.abc.Sequence):
                                tmp = Path._search(obj, path[idx + 1 :], *args, default_value=_not_found_, **kwargs)
                                if tmp is not _not_found_:
                                    obj = tmp
                                    break
                            obj = getattr(obj, "_parent", _not_found_)
                            # Path.__search(obj, [Path.tags.parent], default_value=_not_found_)
                        else:
                            obj = _not_found_

                        break

                    case Path.tags.descendants:
                        # 遍历访问所有叶节点
                        if isinstance(obj, collections.abc.Mapping):
                            obj = {
                                k: Path._search(v, [Path.tags.descendants] + path[idx + 1 :], *args, **kwargs)
                                for k, v in obj.items()
                            }

                        elif isinstance(obj, collections.abc.Iterable):
                            obj = [
                                Path._search(v, [Path.tags.descendants] + path[idx + 1 :], *args, **kwargs) for v in obj
                            ]

                        elif len(path) > 0:
                            obj = Path._search(obj, path[idx + 1 :], *args, **kwargs)

                    case Path.tags.children:
                        if isinstance(obj, collections.abc.Mapping):
                            obj = {k: Path._search(v, path[idx + 1 :], *args, **kwargs) for k, v in obj.items()}

                        elif isinstance(obj, collections.abc.Iterable):
                            obj = [Path._search(v, path[idx + 1 :], *args, **kwargs) for v in obj]

                        else:
                            obj = _not_found_
                        break

                    case Path.tags.slibings:
                        parent = getattr(obj, "_parent", _not_found_)

                        if isinstance(parent, collections.abc.Mapping):
                            obj = {
                                k: Path._search(v, path[idx + 1 :], *args, **kwargs)
                                for k, v in parent.items()
                                if v is not obj
                            }

                        elif isinstance(parent, collections.abc.Iterable):
                            obj = [Path._search(v, path[idx + 1 :], *args, **kwargs) for v in parent if v is not obj]

                        else:
                            obj = []
                        break
                    case Path.tags.root:
                        tmp = obj
                        while tmp is not None and tmp is not _not_found_:
                            tmp = getattr(tmp, "_parent", _not_found_)
                            if tmp is _not_found_ or tmp is None:
                                break
                            else:
                                obj = tmp

            elif isinstance(key, set):
                obj = {k: Path._search(obj, as_path(k)[:] + path[idx + 1 :], **kwargs) for k in key}
                break

            elif hasattr(obj.__class__, "_find_"):
                obj = obj._find_(key, default_value=_not_found_)

            elif isinstance(obj, collections.abc.Mapping):
                obj = obj.get(key, _not_found_)

            elif isinstance(obj, collections.abc.Sequence) and not isinstance(obj, str):
                if isinstance(key, int):
                    if key < len(obj):
                        obj = obj[key]
                    else:
                        obj = _not_found_
                elif isinstance(key, slice):
                    obj = [Path._search(s, path[idx + 1 :], **kwargs) for s in obj[key]]
                    break

                else:
                    idx, value = Path._op_search(obj, key)

                    if idx is None:
                        obj = _not_found_
                    else:
                        obj = value

            else:
                obj = _not_found_
        else:
            yield Path._project(obj, projection=kwargs.get("projection", None))

    @staticmethod
    def _project(target: typing.Any, projection, **kwargs):

        if isinstance(projection, Path.tags):
            projection = getattr(Path, f"_op_{projection.name}", None)

        if callable(projection):
            try:
                res = projection(target, **kwargs)
            except Exception as error:
                raise RuntimeError(f'Fail to call "{projection}"!  ') from error
            else:
                return res

        elif isinstance(projection, str) and projection.isidentifier():
            res = getattr(target, projection, _not_found_)
            if res is _not_found_:
                res = target.get(projection, _not_found_)
            return res

        elif isinstance(projection, int):
            return target[projection]

        elif isinstance(projection, set):
            return {k: Path._project(target, k, **kwargs) for k in projection}

        elif isinstance(projection, list):
            return [Path._project(target, k, **kwargs) for k in projection]

        elif isinstance(projection, dict):
            return {k: Path._project(target, v, **kwargs) for k, v in projection.items()}

        elif projection is None:
            return target

        else:
            raise RuntimeError(f"Unkonwn projection {projection}")

    ####################################################
    # operation

    @staticmethod
    def _op_is_leaf(source: typing.Any, *args, **kwargs) -> bool:
        return not isinstance(source, (collections.abc.Mapping, collections.abc.Sequence))

    @staticmethod
    def _op_is_list(source: typing.Any, *args, **kwargs) -> bool:
        return isinstance(source, collections.abc.Sequence)

    @staticmethod
    def _op_is_dict(source: typing.Any, *args, **kwargs) -> bool:
        return isinstance(source, collections.abc.Mapping)

    @staticmethod
    def _op_check_type(source: typing.Any, tp, *args, **kwargs) -> bool:
        return isinstance_generic(source, tp)

    @staticmethod
    def _op_count(source: typing.Any, *args, **kwargs) -> int:
        if source is _not_found_:
            return 0
        elif (
            isinstance(source, collections.abc.Sequence) or isinstance(source, collections.abc.Mapping)
        ) and not isinstance(source, str):
            return len(source)
        else:
            return 1

    @staticmethod
    def _op_fetch(source: typing.Any, *args, default_value=_not_found_, **kwargs) -> bool:
        if source is _not_found_:
            source = default_value
        return source

    @staticmethod
    def _op_exists(source: typing.Any, *args, **kwargs) -> bool:
        return source is not _not_found_

    @staticmethod
    def _op_search(source: typing.Iterable, *args, search_range=None, **kwargs):
        if not isinstance(source, collections.abc.Sequence):
            raise TypeError(f"{type(source)} is not sequence")

        query = Query(*args, **kwargs)

        if search_range is not None and isinstance(source, collections.abc.Sequence):
            source = source[search_range]

        for idx, value in enumerate(source):
            if query.check(value):
                break
        else:
            idx = None
            value = _not_found_

        return idx, value

    @staticmethod
    def _op_call(source, *args, **kwargs) -> typing.Any:
        if not callable(source):
            logger.error(f"Not callable! {source}")
            return _not_found_
        else:
            return source(*args, **kwargs)

    @staticmethod
    def _op_next(target, query, start: int | None = None, *args, **kwargs) -> typing.Tuple[typing.Any, int | None]:
        if not isinstance(query, (slice, set, Query)):
            raise ValueError(f"query is not dict,slice! {query}")

        if target is _not_found_ or target is None:
            return _not_found_, None

        if isinstance(query, slice):
            if start is None or start is _not_found_:
                start = query.start or 0
            elif query.start is not None and start < query.start:
                raise IndexError(f"Out of range: {start} < {query.start}!")
            stop = query.stop or len(target)
            step = query.step or 1

            if start >= stop:
                # raise StopIteration(f"Can not find next entry of {start}>={stop}!")
                return None, None
            else:
                value = Path._op_fetch(target, start, *args, default_value=_not_found_, **kwargs)

                if value is _not_found_:
                    start = None
                else:
                    start += step

                return value, start

        elif isinstance(query, Query):
            if start is None or start is _not_found_:
                start = 0

            stop = len(target)

            value = _not_found_

            while start < stop:
                value = target[start]
                if not Path._op_check(value, query, *args, **kwargs):
                    start += 1
                    continue
                else:
                    break

            if start >= stop:
                return _not_found_, None
            else:
                return value, start

        else:
            raise NotImplementedError(f"Not implemented yet! {type(query)}")


PathLike = str | int | slice | dict | list | OpTags | Path | None

PathItemLike = str | int | slice | dict | OpTags

path_like = tuple([int, str, slice, list, tuple, set, dict, OpTags, Path])


_T = typing.TypeVar("_T")


def update_tree(target: _T, *args, **kwargs) -> _T:
    for d in [*args, kwargs]:
        target = Path._delete(target, [], d)
    return target


def merge_tree(*args, **kwargs) -> _T:
    return update_tree({}, *args, **kwargs)


def as_path(path):
    if path is None or path is _not_found_:
        return Path()
    elif not isinstance(path, Path):
        return Path(path)
    else:
        return path
