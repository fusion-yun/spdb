from __future__ import annotations

import tempfile
import shutil
import pathlib
import os
import typing
import numpy as np
import uuid
import contextlib
from ..view import View as sp_view
from .Expression import Expression
from .TimeSeries import TimeSeriesAoS, TimeSlice
from .sp_property import SpTree, sp_property

from ..utils.logger import logger
from ..utils.plugin import Pluggable
from ..utils.envs import SP_MPI, SP_DEBUG, SP_LABEL
from ..utils.tree_utils import traversal_tree


class Actor(SpTree, Pluggable):
    mpi_enabled = False
    _plugin_prefix = __package__
    _plugin_registry = {}

    def __init__(self, *args, **kwargs) -> None:
        Pluggable.__init__(self, *args, **kwargs)
        SpTree.__init__(self, *args, **kwargs)
        self._inputs = {}
        self._uid = uuid.uuid3(uuid.uuid1(clock_seq=0), self.__class__.__name__)

    @property
    def tag(self) -> str:
        return f"{self._plugin_prefix}{self.__class__.__name__.lower()}"

    @property
    def MPI(self):
        return SP_MPI

    def _repr_svg_(self) -> str:
        try:
            res = sp_view.display(self, output="svg")
        except Exception as error:
            logger.error(error)
            res = None
        return res

    def __geometry__(self, *args, **kwargs):
        return {}, {}

    @contextlib.contextmanager
    def working_dir(self, suffix: str = "", prefix="") -> str:
        temp_dir = None
        if SP_DEBUG:
            _working_dir = f"{self.output_dir}/{prefix}{self.tag}{suffix}"
            pathlib.Path(_working_dir).mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix=self.tag)
            _working_dir = temp_dir.name

        pwd = os.getcwd()

        os.chdir(_working_dir)

        logger.info(f"Enter directory {_working_dir}")

        error = None

        try:
            yield _working_dir
        except Exception as e:
            error = e

        if error is not None and temp_dir is not None:
            shutil.copytree(temp_dir.name, f"{self.output_dir}/{self.tag}{suffix}", dirs_exist_ok=True)
        elif temp_dir is not None:
            temp_dir.cleanup()

        os.chdir(pwd)
        logger.info(f"Enter directory {pwd}")

        if error is not None:
            raise RuntimeError(
                f"Failed to execute actor {self.tag}! see log in {self.output_dir}/{self.tag}"
            ) from error

    @property
    def output_dir(self) -> str:
        return (
            self.get("output_dir", None)
            or os.getenv("SP_OUTPUT_DIR", None)
            or f"{os.getcwd()}/{SP_LABEL.lower()}_output"
        )

    @property
    def uid(self) -> int:
        return self._uid

    def __hash__(self) -> int:
        """
        hash 值代表 Actor 状态 stats
        Actor 状态由所有依赖 dependence 的状态决定
        time 时第一个 dependence
        """
        iteration = self.time_slice.current.iteration if self.time_slice.is_initializied else 0
        return hash(
            ":".join([str(self.uid), str(iteration), str(self.status)] + [str(hash(v)) for v in self._inputs.values()])
        )

    @property
    def time(self) -> float | None:
        return self._inputs.get("time", 0.0)

    """ 时间戳，代表 Actor 所处时间，用以同步"""

    @property
    def status(self) -> int:
        return self._inputs.get("status", 0)

    """ 执行状态， 用于异步调用
        0: success 任务完成
        1: working 任务执行中
       -1: failed  任务失败  
    """

    @property
    def dependences(self) -> typing.List[Actor]:
        return self._inputs

    time_slice: TimeSeriesAoS[TimeSlice] = sp_property()

    def execute(self, current: TimeSlice, *previous: typing.Tuple[TimeSlice], **inputs) -> typing.Type[Actor]:
        """初始化 Actor，
        kwargs中不应包含 Actor 对象作为 input
        """
        return self

    def refresh(self, *args, time=None, **inputs) -> typing.Type[Actor]:
        """
        inputs : 输入， Actor 的状态依赖其输入
        """

        self._inputs.update(inputs)

        self.time_slice.current.refresh(*args, time=time)

        self.execute(self.time_slice.current, self.time_slice.previous, **self._inputs)

        return self

    def advance(self, *args, time=None, **kwargs) -> typing.Type[Actor]:
        self._inputs = kwargs

        self.time_slice.advance(*args, time=time)

        self.execute(self.time_slice.current, self.time_slice.previous, **self._inputs)

        return self

    def fetch(self, *args, slice_index=0, **kwargs) -> typing.Type[TimeSlice]:
        """
        获取 Actor 的输出
        """
        t = self.time_slice.get(slice_index)
        if not isinstance(t, SpTree):
            return t
        else:
            return t.clone(*args, **kwargs)
