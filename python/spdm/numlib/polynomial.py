from spdm.utils.type_hint import array_type
from spdm.core.expression import Expression


class Polynomials(Expression):
    """A wrapper for numpy.polynomial
    TODO: imcomplete
    """

    def __init__(
        self,
        coeff,
        *args,
        kind: str = None,
        domain=None,
        window=None,
        symbol="x",
        preprocess=None,
        postprocess=None,
        **kwargs,
    ) -> None:
        match kind:
            case "chebyshev":
                from numpy.polynomial.chebyshev import Chebyshev

                PPolyOp = Chebyshev
            case "hermite":
                from numpy.polynomial.hermite import Hermite

                PPolyOp = Hermite
            case "hermite":
                from numpy.polynomial.hermite_e import HermiteE

                PPolyOp = HermiteE
            case "laguerre":
                from numpy.polynomial.laguerre import Laguerre

                PPolyOp = Laguerre
            case "legendre":
                from numpy.polynomial.legendre import Legendre

                PPolyOp = Legendre
            case _:  # "power"
                import numpy.polynomial.polynomial as polynomial

                PPolyOp = polynomial

        op = PPolyOp(coeff, domain=domain, window=window, symbol=symbol)

        super().__init__(op, *args, **kwargs)
        self._preprocess = preprocess
        self._postprocess = postprocess

    def _eval(self, x: array_type | float) -> array_type | float:

        if not isinstance(x, (array_type, float)):
            return super().__call__(x)

        if self._preprocess is not None:
            x = self._preprocess(x)

        y = self._op(x)

        if self._postprocess is not None:
            y = self._postprocess(y)

        return y
