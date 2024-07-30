import typing
from copy import copy
import numpy as np
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, NumericType, array_type, is_scalar

from spdm.core.path import Path
from spdm.core.entry import Entry
from spdm.core.htree import HTreeNode, HTree
from spdm.core.domain import Domain
from spdm.core.functor import Functor


class Expression(HTreeNode):
    """Expression

    表达式是由多个操作数和运算符按照约定的规则构成的一个序列。
    其中运算符表示对操作数进行何种操作，而操作数可以是变量、常量、数组或者表达式。
    表达式可以理解为树状结构，每个节点都是一个操作数或运算符，每个节点都可以有多个子节点。
    表达式的值可以通过对树状结构进行遍历计算得到。
    没有子节点的节点称为叶子节点，叶子节点可以是常量、数组，也可以是变量和函数。

    变量是一种特殊的函数，它的值由上下文决定。

    例如：
        >>> import spdm
        >>> x = spdm.core.Expression(np.sin)
        >>> y = spdm.core.Expression(np.cos)
        >>> z = x + y
        >>> z
        <Expression   op="add" />
        >>> z(0.0)
        3.0


    """

    _domain_class = Domain

    def __new__(cls, *args, **kwargs) -> typing.Self:
        if cls is not Expression or len(args) == 0:
            return object.__new__(cls)

        if isinstance(args[0], (bool, int, float, complex)):
            return Scalar.__new__(cls, *args, **kwargs)
        elif callable(args[0]):
            return object.__new__(cls)
        else:
            from spdm.core.function import Function

            return object.__new__(Function)

    def __init__(
        self,
        op_or_value,
        *children: typing.Self,
        domain: Domain = None,
        _entry: Entry = None,
        _parent: HTreeNode = None,
        **kwargs,
    ) -> None:
        """初始化表达式

        Args:
            op (Callable|array_type): 值或者算子
            domain (Domain, optional): 定义域. Defaults to None.
        """
        if not callable(op_or_value):
            value = op_or_value
            op = None
        else:
            value = _not_found_
            op = op_or_value

        super().__init__(value, _entry=_entry, _parent=_parent)

        self._op = op  # 表达式算符
        self._children = children  # 构成表达式的子节点
        self._domain = domain  # 定义域
        self._ppoly = None  # 表达式的近似多项式，缓存
        self._kwargs = kwargs

    def __copy__(self) -> typing.Self:
        """复制一个新的 Expression 对象"""
        other: Expression = super().__copy__()
        other._op = self._op
        other._children = self._children
        other._domain = self._domain
        other._ppoly = self._ppoly
        other._kwargs = self._kwargs

        return other

    @property
    def name(self) -> str:
        return self._kwargs.get("name", "unnamed")

    @property
    def __label__(self) -> str:
        return self._kwargs.get("label", None) or self._kwargs.get("name", None) or self.__class__.__name__

    @property
    def domain(self) -> Domain:
        """返回表达式的定义域"""
        if isinstance(self._domain, Domain):
            return self._domain

        t_domain = self._domain

        obj = self._parent

        while t_domain is None and obj is not None:
            if (domain := getattr(obj, "domain", None)) is None:
                obj = getattr(obj, "_parent", None)
            else:
                t_domain = domain
                break

        if t_domain is None and len(self._children) > 0:
            # 从构成表达式的子节点查找 domain
            # TODO: 根据子节点 domain 的交集确定表达式的 domain
            for child in self._children:
                t_domain = getattr(child, "domain", None)
                if t_domain is not None:
                    break

        if t_domain is not None and not isinstance(t_domain, Domain):
            t_domain = self.__class__._domain_class(t_domain)

        self._domain = t_domain

        return self._domain

    @property
    def has_children(self) -> bool:
        """判断是否有子节点"""
        return len(self._children) > 0

    @property
    def empty(self) -> bool:
        return not self.has_children and self._op is None

    def __repr__(self) -> str:
        return self._render_latex_()

    def __str__(self) -> str:
        return self._render_latex_()

    def _render_latex_(self) -> str:
        vargs = []
        for expr in self._children:
            if isinstance(expr, (bool, int, float, complex)):
                res = str(expr)
            elif expr is None:
                res = "n.a"
            elif isinstance(expr, np.ndarray):
                if len(expr.shape) == 0:
                    res = f"{expr.item()}"
                else:
                    res = f"{expr.dtype}[{expr.shape}]"
            elif isinstance(expr, Variable):
                res = expr.__label__

            elif isinstance(expr, Expression):
                res = expr._render_latex_()
            elif isinstance(expr, np.ufunc):
                res = expr.__name__
            else:
                res = expr.__class__.__name__
            vargs.append(res)

        if isinstance(self._op, np.ufunc):
            op_tag = EXPR_OP_TAG.get(self._op.__name__, self._op.__name__)

            if self._op.nin == 1:
                res = rf"{op_tag}{{{vargs[0]}}}"

            elif self._op.nin == 2:
                if op_tag == "/":
                    res = f"\\frac{{{vargs[0]}}}{{{vargs[1]}}}"
                else:
                    res = rf"{{{vargs[0]}}} {op_tag} {{{vargs[1]}}}"
            else:
                raise RuntimeError("Tri-op is not defined!")

        elif (op_tag := self._kwargs.get("label", None) or self._kwargs.get("name", None)) is not None:
            if len(vargs) == 0:
                res = op_tag
            else:
                res: str = rf"{op_tag}\left({','.join(vargs)}\right)"

        else:
            if isinstance(self._op, Expression):
                op_tag = self._op.__label__
            else:
                op_tag = self._op.__class__.__name__

            res: str = rf"{op_tag}\left({','.join(vargs)}\right)"

        return res

    def _repr_latex_(self) -> str:
        """for jupyter notebook display"""
        msg = self._render_latex_().strip("$")
        return f"$${msg}$$"

    @property
    def dtype(self):
        return float

    def __array_ufunc__(self, ufunc, method, *args, **kwargs) -> typing.Self:
        """
        重载 numpy 的 ufunc 运算符, 用于在表达式中使用 numpy 的 ufunc 函数构建新的表达式。
        例如：
            >>> import numpy as np
            >>> import spdm
            >>> x = spdm.core.Expression(np.sin)
            >>> y = spdm.core.Expression(np.cos)
            >>> z = x + y
            >>> z
            <Expression   op="add" />
            >>> z(0.0)
            1.0
        """
        if method != "__call__" or len(kwargs) > 0:
            return Expression(Functor(ufunc, method=method, **kwargs), *args)
        else:
            return Expression(ufunc, *args)

    @property
    def __value__(self) -> array_type | float:
        """在定义域上计算表达式，返回数组。"""
        value = super().__value__
        if value is _not_found_ and self.domain is not None:
            # 缓存表达式结果
            value = self._eval(*self.domain.coordinates)
            self._cache = value
        return value

    def __array__(self, *args, **kwargs) -> array_type:
        return np.asarray(self.__value__, *args, **kwargs)

    def __compile__(self) -> typing.Callable[..., array_type]:
        """返回编译后的表达式，近似插值多项式
        TODO:
        - 支持 JIT 编译, support JIT compile
        - 优化缓存
        - 支持多维插值
        - 支持多维求导，自动微分 auto diff
        - support JIT compilation
        - support broadcasting?
        - support multiple meshes?
        """
        if not callable(self._ppoly):
            # 构建插值多项式近似
            self._ppoly = self.domain.interpolate(self._eval)

        if self._ppoly is None:
            raise RuntimeError(f"Fail to compile {self}")
        return self._ppoly

    def _eval(self, *args):
        # 执行计算
        if not callable(self._op):
            raise RuntimeError("op is null!")

        if len(self._children) == 0:
            xargs = args
        else:
            xargs = []
            for child in self._children:
                try:
                    if callable(child):
                        v = child(*args)
                    else:
                        v = np.asarray(child)

                except RuntimeError as error:
                    raise RuntimeError(f"Failure to calculate  child {child} !") from error
                else:
                    xargs.append(v)

        return self._op(*xargs)

    def __call__(self, *args) -> typing.Self:
        """重载函数调用运算符，用于计算表达式的值"""

        if len(args) == 0:  # 空调用，返回自身
            return self

        elif any([isinstance(a, Expression) for a in args]):  #  创建复合函数
            return Expression(self, *args)

        elif callable(self._ppoly):
            # 若有近似插值多项式，执行
            return self._ppoly(*args)

        else:
            return self._eval(*args)

    # @typing.overload
    # def __call__(self, x: array_type, *args) -> array_type:
    #     pass

    # @typing.overload
    # def __call__(self, x: float, *args) -> float:
    #     pass

    # @typing.overload
    # def __call__(self, x: typing.Self, *args) -> typing.Self:
    #     pass

    # @typing.overload
    # def __call__(self) -> typing.Self:
    #     pass

    def derivative(self, order: int, **kwargs):
        """导数"""
        return Expression(self.__compile__().derivative(order), label=f"d{self.__label__}", **kwargs)

    def antiderivative(self, order: int, **kwargs):
        """不定积分/反导数"""
        return Expression(
            self.__compile__().antiderivative(order), label=f"\\int\\left({self.__label__}\\right)", **kwargs
        )

    def partial_derivative(self, *order: int, **kwargs):
        raise NotImplementedError()

    def pd(self, *order, **kwargs):
        return self.partial_derivative(*order, **kwargs)

    def integral(self, *args, **kwargs) -> float:
        raise NotImplementedError()

    @property
    def d(self) -> typing.Self:
        """1st derivative 一阶导数"""
        return self.derivative(1)

    @property
    def d2(self) -> typing.Self:
        """2nd derivative 二阶导数"""
        return self.derivative(2)

    @property
    def I(self) -> typing.Self:
        """antiderivative 原函数"""
        return self.antiderivative(1)

    @property
    def dln(self) -> typing.Self:
        """logarithmic derivative 对数求导"""
        return self.derivative(1) / self

    def find_roots(self, *args, **kwargs) -> typing.Generator[float, None, None]:
        raise NotImplementedError("TODO: find_roots")

    def fetch(self, *args, _parent=None, **kwargs):
        if len(args) + len(kwargs) == 0:
            if self._cache is not None:
                return self._cache
            else:
                return self.__array__()
        else:
            res = self(*args, **kwargs)

            if res is self:
                res = copy(self)

            if isinstance(res, HTreeNode):
                res._parent = _parent

        return res

    # fmt: off
    # pylint: off
    def __neg__      (self                              )->typing.Self: return Expression(np.negative     ,  self     )
    def __add__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.add          ,  self, o  ) if not ((is_scalar(o) and o == 0 ) or isinstance(o, ConstantZero) or o is _not_found_ and o is None) else self
    def __sub__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.subtract     ,  self, o  ) if not ((is_scalar(o) and o == 0 ) or isinstance(o, ConstantZero) or o is _not_found_ and o is None) else self
    def __mul__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.multiply     ,  self, o  ) if not (is_scalar(o) and (o ==0 or o==1)) else (ConstantZero() if o==0 else self)
    def __matmul__   (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.matmul       ,  self, o  ) if not (is_scalar(o) and (o ==0 or o==1)) else (ConstantZero() if o==0 else self)
    def __truediv__  (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.true_divide  ,  self, o  ) if not (is_scalar(o) and (o ==0 or o==1)) else (Scalar(np.nan) if o==0 else self)
    def __pow__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.power        ,  self, o  ) if not (is_scalar(o) and (o ==0 or o==1)) else (ConstantOne() if o==0 else self)
    def __eq__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.equal        ,  self, o  )
    def __ne__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.not_equal    ,  self, o  )
    def __lt__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.less         ,  self, o  )
    def __le__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.less_equal   ,  self, o  )
    def __gt__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.greater      ,  self, o  )
    def __ge__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.greater_equal,  self, o  )
    def __radd__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.add          ,  o, self  ) if not ((is_scalar(o) and o == 0 ) or isinstance(o, ConstantZero) or o is _not_found_ and o is None) else self
    def __rsub__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.subtract     ,  o, self  ) if not ((is_scalar(o) and o == 0 ) or isinstance(o, ConstantZero) or o is _not_found_ and o is None) else self.__neg__()
    def __rmul__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.multiply     ,  o, self  ) if not (is_scalar(o) and (o ==0 or o==1)) else (ConstantZero() if o==0 else self)
    def __rmatmul__  (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.matmul       ,  o, self  ) if not (is_scalar(o) and (o ==0 or o==1)) else (ConstantZero() if o==0 else self)
    def __rtruediv__ (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.divide       ,  o, self  )
    def __rpow__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.power        ,  o, self  ) if not (is_scalar(o) and o ==1)  else ConstantOne()
    def __abs__      (self                              )->typing.Self: return Expression(np.abs          ,  self     )
    def __pos__      (self                              )->typing.Self: return Expression(np.positive     ,  self     )
    def __invert__   (self                              )->typing.Self: return Expression(np.invert       ,  self     )
    def __and__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.bitwise_and  ,  self, o  ) if not isinstance(o,bool) else ( self if o ==True else False)
    def __or__       (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.bitwise_or   ,  self, o  ) if not isinstance(o,bool) else ( True if o ==True else self)
    def __xor__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.bitwise_xor  ,  self, o  )
    def __rand__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.bitwise_and  ,  o, self  ) if not isinstance(o,bool) else ( self if o ==True else False)
    def __ror__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.bitwise_or   ,  o, self  ) if not isinstance(o,bool) else ( True if o ==True else self)
    def __rxor__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.bitwise_xor  ,  o, self  )
    def __rshift__   (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.right_shift  ,  self, o  )
    def __lshift__   (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.left_shift   ,  self, o  )
    def __rrshift__  (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.right_shift  ,  o, self  )
    def __rlshift__  (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.left_shift   ,  o, self  )
    def __mod__      (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.mod          ,  self, o  )
    def __rmod__     (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.mod          ,  o, self  )
    def __floordiv__ (self, o: NumericType | typing.Self)->typing.Self: return Expression(np.floor_divide ,  self, o  )
    def __rfloordiv__(self, o: NumericType | typing.Self)->typing.Self: return Expression(np.floor_divide ,  o, self  )
    def __trunc__    (self                              )->typing.Self: return Expression(np.trunc        ,  self     )
    def __round__    (self, n=None                      )->typing.Self: return Expression(np.round        ,  self, n  )
    def __floor__    (self                              )->typing.Self: return Expression(np.floor        ,  self     )
    def __ceil__     (self                              )->typing.Self: return Expression(np.ceil         ,  self     )
    # pylint: on
    # fmt: on


EXPR_OP_TAG = {
    "negative": "-",
    "add": "+",
    "subtract": "-",
    "multiply": r"\cdot",
    "matmul": r"\cdot",
    "divide": "/",
    "power": "^",
    "abs": "",
    "absolute": "abs",
    "positive": "+",
    # "invert": "",
    "bitwise_and": "&",
    "bitwise_or": "|",
    # "bitwise_xor": "",
    # "right_shift": "",
    # "left_shift": "",
    # "right_shift": "",
    # "left_shift": "",
    "mod": "%",
    # "floor_divide": "",
    # "floor_divide": "",
    # "trunc": "",
    # "round": "",
    # "floor": "",
    # "ceil": "",
    "sqrt": r"\sqrt",
}


class Variable(Expression):
    """Variable

    变量是一种特殊的函数，它的值由上下文决定。
    例如：
    >>> import spdm
    >>> x = spdm.core.Variable(0,"x")
    >>> y = spdm.core.Variable(1,"y")
    >>> z = x + y
    >>> z
    <Expression   op="add" />
    >>> z(0.0, 1.0)
    1.0

    """

    def __init__(self, idx: int | str, name: str = None, **kwargs) -> None:
        if name is None:
            name = idx if isinstance(idx, str) else f"_{idx}"
        super().__init__(None, name=name, **kwargs)
        self._idx = idx

    def __copy__(self) -> typing.Self:
        res = super().__copy__()
        res._idx = self._idx
        return res

    @property
    def _type_hint(self) -> typing.Type:
        """获取函数的类型"""
        orig_class = getattr(self, "__orig_class__", None)
        if orig_class is not None:
            return typing.get_args(orig_class)[0]
        else:
            return float

    @property
    def index(self):
        return self._idx

    def __call__(self, *args, **kwargs):
        if all([isinstance(a, Variable) for a in args]):
            res = self
        elif len(args) == 1 and isinstance(args[0], HTree):
            pth = Path(self.__name__)
            res = pth.get(args[0], _not_found_)
            if res is _not_found_:
                res = pth.get(kwargs, _not_found_)
            if res is _not_found_:
                raise RuntimeError(f"Can not get variable {self.__name__}")
        elif self._idx < len(args):
            res = args[self._idx]
        elif self.__name__.isidentifier():
            res = kwargs.get(self.__name__)
        else:
            raise RuntimeError(
                f"Variable {self.__label__} require {self._idx+1} args, or {self.__name__} in kwargs but only {args} provided!"
            )

        return res

    def _flush(self):
        self._cache = self(*self.domain.coordinates)

    def __repr__(self) -> str:
        return self.__label__


_x = Variable(0, "x")
_y = Variable(1, "y")
_z = Variable(2, "z")


class Scalar(Expression):
    """标量"""

    # def __init__(self, *args, **kwargs) -> None:
    #     if not isinstance(value, (float, int, bool, complex)):
    #         raise ValueError(f"value should be float|int|bool|complex, but got {type(value)}!")
    #     super().__init__(value, **kwargs)

    @property
    def __label__(self):
        return self._cache

    def __array__(self) -> ArrayType:
        return np.array(self._cache)

    def __str__(self):
        return str(self._cache)

    def __repr__(self) -> str:
        return str(self._cache)

    def __equal__(self, other) -> bool:
        return self._cache == other

    def __call__(self, *args):
        shape = [(a.shape if isinstance(a, np.ndarray) else 1) for a in args]
        if all(s == 1 for s in shape):
            return self._cache
        elif all(shape[0] == s for s in shape[1:]):
            return np.full(shape[0], self._cache)
        else:
            raise RuntimeError(f"Illegal shape {shape}")

    def derivative(self, *args, **kwargs):
        return ConstantZero(_parent=self._parent, **kwargs)


class ConstantZero(Scalar):
    """常数 0"""

    def __init__(self, **kwargs):
        super().__init__(0, **kwargs)

    # fmt: off
    def __neg__      (self                             ) ->Expression : return self
    def __add__      (self, o: NumericType | Expression) ->Expression : return o
    def __sub__      (self, o: NumericType | Expression) ->Expression : return Expression(np.negative     ,  o  ) 
    def __mul__      (self, o: NumericType | Expression) ->Expression : return self
    def __matmul__   (self, o: NumericType | Expression) ->Expression : return self
    def __truediv__  (self, o: NumericType | Expression) ->Expression : return self
    def __pow__      (self, o: NumericType | Expression) ->Expression : return self
    def __radd__     (self, o: NumericType | Expression) ->Expression : return o
    def __rsub__     (self, o: NumericType | Expression) ->Expression : return o
    def __rmul__     (self, o: NumericType | Expression) ->Expression : return self
    def __rmatmul__  (self, o: NumericType | Expression) ->Expression : return self
    def __rtruediv__ (self, o: NumericType | Expression) ->Expression : return Scalar(np.nan)
    def __rpow__     (self, o: NumericType | Expression) ->Expression : return one
    def __abs__      (self                             ) ->Expression : return self
    # fmt: on


class ConstantOne(Scalar):
    """常数 1"""

    def __init__(self, **kwargs):
        super().__init__(1, **kwargs)

    # fmt: off
    def __neg__      (self                             ) ->Expression: return Scalar(-1)
    def __mul__      (self, o: NumericType | Expression) ->Expression: return o
    def __matmul__   (self, o: NumericType | Expression) ->Expression: return o
    def __pow__      (self, o: NumericType | Expression) ->Expression: return self
    def __rmul__     (self, o: NumericType | Expression) ->Expression: return o
    def __rmatmul__  (self, o: NumericType | Expression) ->Expression: return o
    def __rtruediv__ (self, o: NumericType | Expression) ->Expression: return o
    def __rpow__     (self, o: NumericType | Expression) ->Expression: return o
    def __abs__      (self                             ) ->Expression: return self
    # fmt: on


zero = ConstantZero()

one = ConstantOne()
