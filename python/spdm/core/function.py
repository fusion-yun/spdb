import typing
from spdm.utils.logger import logger
from spdm.utils.type_hint import array_type
from spdm.utils.tags import _not_found_
from spdm.core.expression import Expression
from spdm.core.domain import DomainPPoly, Domain


class Function(Expression):
    """
    Function

    A function is a mapping between two sets, the _domain_ and the  _value_.
    The _value_  is the set of all possible outputs of the function.
    The _domain_ is the set of all possible inputs  to the function.

    函数定义域为多维空间时，网格采用rectlinear mesh，即每个维度网格表示为一个数组 _dims_ 。
    """

    _domain_class = DomainPPoly

    def __init__(self, *args, domain: Domain = None, **kwargs):

        if len(args) > 1:
            if domain is not None:
                raise RuntimeError(f"Too much args! {args}")
            domain = DomainPPoly(*args[:-1])

        super().__init__(*args[-1:], domain=domain, **kwargs)
        if self._cache is _not_found_ and self._entry is not None:
            self._cache = self._entry.get()
        # if self._cache is _not_found_ and self.domain is not None:
        #     self._cache = np.full(self.domain.shape, np.nan)

    def __getitem__(self, idx) -> float:
        return self._cache[idx]

    def __setitem__(self, idx, value) -> None:
        assert self._op is not None, f"Function is not changable! op={self._op}"
        self._ppoly = None
        self._cache[idx] = value

    def __compile__(self) -> typing.Callable[..., array_type]:
        """对函数进行编译，用插值函数替代原始表达式，提高运算速度
        - 由 points，value  生成插值函数，并赋值给 self._op
        插值函数相对原始表达式的优势是速度快，缺点是精度低。
        """
        if self._ppoly is None:  # not callable(self._ppoly):
            if callable(self._op):
                self._ppoly = self.domain.interpolate(self._op)
            else:
                if self._cache is _not_found_ and self._entry is not None:
                    self._cache = self._entry.get()
                if self._cache is _not_found_:
                    raise RuntimeError(f"Invalid cache! {self._cache}")
                self._ppoly = self.domain.interpolate(self._cache)

        return self._ppoly

    def _eval(self, *args) -> array_type:
        if callable(self._ppoly):
            return self._ppoly(*args)
        elif callable(self._op):
            return self._op(*args)
        else:
            return self.__compile__()(*args)

    def validate(self, value=None, strict=False) -> bool:
        """检查函数的定义域和值是否匹配"""

        m_shape = tuple(self.shape)

        v_shape = ()

        if value is None:
            value = self._cache

        if value is None:
            raise RuntimeError(f" value is None! {self}")

        if isinstance(value, array_type):
            v_shape = tuple(value.shape)

        if (v_shape == m_shape) or (v_shape[:-1] == m_shape):
            return True
        elif strict:
            raise RuntimeError(f" value.shape is not match with dims! {v_shape}!={m_shape} ")
        else:
            logger.warning(f" value.shape is not match with dims! {v_shape}!={m_shape} ")
            return False
