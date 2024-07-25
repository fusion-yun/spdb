from spdm.utils.type_hint import array_type
from spdm.core.function import Function
from spdm.core.sp_tree import sp_tree, annotation


@sp_tree
class Signal:
    """Signal with its time base"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._func = None

    @property
    def name(self) -> str:
        return self._metadata.get("name", "")

    data: array_type

    time: array_type = annotation(units="s")

    def __call__(self, t: float) -> float:
        if self._func is None:
            self._func = Function(self.time, self.data)
        return self._func(t)


class SignalND(Signal):
    pass
