import typing
from .actor import Actor
from dask.distributed import Client

_T = typing.TypeVar("_T")


class TaskManager:
    def __init__(self) -> None:
        self._client = Client()

    def submit_actor(self, cls: typing.Type[Actor]) -> None:

        return self._client.submit(cls, actor=True)
