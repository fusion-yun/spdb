import typing
import inspect

from spdm.core.pluggable import Pluggable
from spdm.core.sp_tree import SpTree, PropertyTree, sp_property


class SpObject(SpTree, Pluggable):
    """对象的基类/抽象类"""

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of SpObject.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            typing.Type[typing.Self]: The new instance of SpObject.
        """

        cls_name = (
            args[0].get("$class", None) if len(args) == 1 and isinstance(args[0], dict) else kwargs.get("plugin", None)
        )

        return super().__new__(cls, cls_name)

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the SpObject.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        SpTree.__init__(self, *args, **kwargs)

    @sp_property
    def metadata(self) -> PropertyTree:
        """
        Return the metadata.

        Returns:
            PropertyTree: The metadata.
        """
        return self._metadata


_T = typing.TypeVar("_T")


def sp_object(cls: _T = None, /, **kwargs) -> _T:
    """
    Decorator to convert cls into SpObject.

    Args:
        cls: The class to be converted.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        _T: The converted class.
    """

    from spdm.core.sp_tree import _process_sptree

    def wrap(_cls, _kwargs=kwargs):
        if not inspect.isclass(_cls):
            raise TypeError(f"Not a class {_cls}")

        if not issubclass(_cls, SpObject):
            n_cls = type(_cls.__name__, (_cls, SpObject), {})
            n_cls.__module__ = _cls.__module__
        else:
            n_cls = _cls

        n_cls = _process_sptree(n_cls, **_kwargs)

        return n_cls

    if cls is None:
        return wrap
    else:
        return wrap(cls)
