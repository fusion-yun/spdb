import abc


class WithCategory(abc.ABC):

    def __init_subclass__(cls, /, category: str = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.category = category

    def __hash__(self) -> int:
        return hash(self.category)
