import collections.abc
import typing
from enum import Flag, auto
import numpy as np

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import isinstance_generic


class Query:
    class tags(Flag):  # pylint: disable=C0103
        call = auto()  # call function
        exists = auto()
        is_leaf = auto()
        is_list = auto()
        is_dict = auto()
        check_type = auto()  # check type
        get_key = auto()  # 返回键
        get_value = auto()  # 返回值
        set_value = auto()  # 返回值
        get_item = auto()  # 返回键和值
        set_item = auto()  # 返回键和值

        first_valid = auto()  # 返回第一个有效值，若无则返回 _not_found_
        last_valid = auto()  # 返回最后一个有效值，若无则返回 _not_found_
        search = auto()  # search by query return idx
        dump = auto()  # rescurive get all data

        # for sequence
        reduce = auto()
        sort = auto()

        # predicate 谓词
        check = auto()
        count = auto()

        # boolean
        equal = auto()
        le = auto()
        ge = auto()
        less = auto()
        greater = auto()

    def __init__(self, query=None, **kwargs) -> None:
        if query is _not_found_ or query is None:
            query = {}
        if isinstance(query, Query):
            self._query = Query._parser(query._query, **kwargs)
        else:
            self._query = Query._parser(query, **kwargs)

    def __str__(self) -> str:
        p = self._query

        if not isinstance(p, dict):
            return str(p)
        else:
            m_str = ",".join([f"{k}={Path._to_str(v)}" for k, v in p.items()])
            return f"?{m_str} "

    def __equal__(self, other: typing.Self) -> bool:
        return self._query == other._query if isinstance(other, Query) else False

    @classmethod
    def _parser(cls, query, **kwargs) -> dict:
        if query is None:
            query = {".": Query.tags.get_value}

        elif isinstance(query, Query.tags):
            query = {".": f"${query.name}"}

        elif isinstance(query, str) and query.startswith("$"):
            query = {".": query}

        elif isinstance(query, str):
            query = {"@id": query}

        elif isinstance(query, dict):
            query = {k: Query._parser(v) for k, v in query.items()}

        elif isinstance(query, slice):
            pass
        else:
            raise TypeError(f"{(query)}")

        if isinstance(query, dict):
            query.update(kwargs)

        return query

    def __call__(self, target, *args, **kwargs) -> typing.Any:
        return self.check(target, *args, **kwargs)

    @staticmethod
    def _eval_one(target, k, v) -> typing.Any:
        res = False
        if isinstance(k, str):
            if k.startswith("@") and hasattr(target.__class__, k[1:]):
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

    ####################################################
    # operation

    @staticmethod
    def is_leaf(source: typing.Any, *args, **kwargs) -> bool:
        return not isinstance(source, (collections.abc.Mapping, collections.abc.Sequence))

    @staticmethod
    def is_list(source: typing.Any, *args, **kwargs) -> bool:
        return isinstance(source, collections.abc.Sequence)

    @staticmethod
    def is_dict(source: typing.Any, *args, **kwargs) -> bool:
        return isinstance(source, collections.abc.Mapping)

    @staticmethod
    def check_type(source: typing.Any, tp, *args, **kwargs) -> bool:
        return isinstance_generic(source, tp)

    @staticmethod
    def count(source: typing.Any, *args, **kwargs) -> int:
        if source is _not_found_:
            return 0
        elif (
            isinstance(source, collections.abc.Sequence) or isinstance(source, collections.abc.Mapping)
        ) and not isinstance(source, str):
            return len(source)
        else:
            return 1

    @staticmethod
    def fetch(source: typing.Any, *args, default_value=_not_found_, **kwargs) -> bool:
        if source is _not_found_:
            source = default_value
        return source

    @staticmethod
    def equal(source: typing.Any, other, *args, **kwargs) -> bool:
        return source == other

    @staticmethod
    def exists(source: typing.Any, *args, **kwargs) -> bool:
        return source is not _not_found_

    @staticmethod
    def search(source: typing.Iterable, *args, search_range=None, **kwargs):
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
    def call(source, *args, **kwargs) -> typing.Any:
        if not callable(source):
            logger.error(f"Not callable! {source}")
            return _not_found_
        return source(*args, **kwargs)

    @staticmethod
    def next(target, query, start: int | None = None, *args, **kwargs) -> typing.Tuple[typing.Any, int | None]:
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
                value = Path.fetch(target, start, *args, default_value=_not_found_, **kwargs)

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


QueryLike = dict | str | Query.tags | None


def as_query(query=None, **kwargs) -> Query | slice:
    if isinstance(query, slice):
        return query
    elif isinstance(query, Query):
        return query
    else:
        return Query(query, **kwargs)
