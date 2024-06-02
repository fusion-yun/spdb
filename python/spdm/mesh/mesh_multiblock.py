import typing

from numpy.typing import ArrayLike, NDArray

from ..core.container import Container
from ..core.function import Function
from ..core.mesh import Mesh


class MultiBlockMesh(Container[Mesh]):

    def __init__(self, block_list: typing.List[typing.Any],  **kwargs) -> None:
        super().__init__(block_list, **kwargs)

        self._cond_list = cond_list
        self._Mesh_list: typing.List[Mesh] = Mesh_list

    def interpolator(self, *args, **kwargs) -> Function:
        return self._cond_list


class MultiBlockFunction(Function):

    def __init__(self, block_list: typing.List[typing.Any], **kwargs) -> None:
        super().__init__(**kwargs)

        self._Mesh_list: MultiBlockMesh = cond_list
        self._data_list: typing.List[Mesh] = Mesh_list

    def __call__(self, *args, **kwargs) -> ArrayLike | NDArray:

        return super().__call__(*args, **kwargs)
