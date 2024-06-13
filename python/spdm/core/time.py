class Time:

    def __init__(self, value: float = 0.0) -> None:
        self._value = value

    def __float__(self) -> float:
        return self._value
