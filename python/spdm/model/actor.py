import tempfile
import shutil
import pathlib
import os
import typing
import contextlib

from spdm.utils.logger import logger
from spdm.utils.envs import SP_DEBUG, SP_LABEL

from spdm.core.path import Path
from spdm.core.domain import Domain
from spdm.core.generic import Generic

from spdm.model.port import Ports
from spdm.model.entity import Entity
from spdm.model.time_sequence import TimeSequence, TimeSlice

_TSlice = typing.TypeVar("_TSlice", bound=TimeSlice)


class Actor(Generic[_TSlice], Entity):
    """执行体，追踪一个随时间演化的对象，
    - 其一个时间点的状态树称为 __时间片__ (time_slice)，由时间片的构成的序列，代表状态演化历史。
    - Actor 通过 in_ports 和 out_ports 与其他 Actor 交互。
    - Actor 通过 fetch 获得其在 domain 上的值。
    - current 返回当前状态，previous 返回历史状态。
    - refresh 更新当前状态，finalize 完成。
    - working_dir 进入工作目录
    - fetch 在 domain 上取值
    - output_dir 输出目录
    - context 获取当前 Actor 所在的 Context。

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    in_ports: Ports
    """输入的 Edge，记录对其他 Actor 的依赖。"""

    out_ports: Ports
    """输出的 Edge，可视为对于引用（reference）的记录"""

    TimeSlice = _TSlice

    time_slice: TimeSequence[_TSlice]
    """时间片序列，保存 Actor 历史状态。
        @note: TimeSeriesAoS 长度为 n(=3) 循环队列。当压入序列的 TimeSlice 数量超出 n 时，会调用 TimeSeriesAoS.__full__(first_slice)
        """

    @property
    def current(self) -> _TSlice:
        """当前时间片，指向 Actor 所在时间点的状态。"""
        return self.time_slice.current

    @property
    def previous(self) -> typing.Generator[_TSlice, None, None]:
        """倒序返回前面的时间片，"""
        yield from self.time_slice.previous

    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return self._parent.context if isinstance(self._parent, Actor) else None

    def initialize(self, *args, **kwargs) -> None:
        """初始化 Actor 。"""
        self.time_slice.initialize(*args, **kwargs)
        self.in_ports.connect(self.context)

    def preprocess(self, **kwargs) -> _TSlice:
        """Actor 的预处理，若需要，可以在此处更新 Actor 的状态树。"""
        self.in_ports.connect(**kwargs)
        return self.time_slice.current

    def execute(self, current: _TSlice, previous: typing.Generator[_TSlice, None, None] = None) -> _TSlice:
        """根据 inports 和 前序 time slice 更新当前time slice"""
        return current

    def postprocess(self, current: _TSlice) -> _TSlice:
        """Actor 的后处理，若需要，可以在此处更新 Actor 的状态树。
        @param current: 当前时间片
        @param working_dir: 工作目录
        """
        return current

    def refresh(self, *args, **kwargs) -> _TSlice:
        """更新当前 Actor 的状态。
        更新当前状态树 （time_slice），并执行 self.iteration+=1
        """

        current = self.preprocess(*args, **kwargs)

        current = self.execute(current, self.time_slice.previous)

        current = self.postprocess(current)

        return current

    def finalize(self) -> None:
        """完成。"""
        self.time_slice.flush()
        self.time_slice.finalize()

    def fetch(self, domain: Domain = None, project: dict | set | tuple = None) -> _TSlice:
        """返回当前在 domain 上的值 _TSlice，默认返回结构为 time_slice.current"""

        if domain is None:
            t_slice = self.current
        else:
            raise NotImplementedError("")

        if project is not None:
            return Path().get(t_slice, project)
        else:
            return t_slice

    @contextlib.contextmanager
    def working_dir(self, suffix: str = "", prefix="") -> typing.Generator[pathlib.Path, None, None]:
        pwd = pathlib.Path.cwd()

        working_dir = f"{self.output_dir}/{prefix}{self.tag}{suffix}"

        temp_dir = None

        if SP_DEBUG:
            current_dir = pathlib.Path(working_dir)
            current_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix=self.tag)
            current_dir = pathlib.Path(temp_dir.name)

        os.chdir(current_dir)

        logger.info(f"Enter directory {current_dir}")

        try:
            yield current_dir
        except FileExistsError as error:
            if temp_dir is not None:
                shutil.copytree(temp_dir.name, working_dir, dirs_exist_ok=True)
            os.chdir(pwd)
            logger.info(f"Enter directory {pwd}")
            logger.error(f"Failed to execute actor {self.tag}! \n See log in {working_dir} ", exc_info=error)
        else:
            if temp_dir is not None:
                temp_dir.cleanup()

            os.chdir(pwd)
            logger.info(f"Enter directory {pwd}")

    @property
    def output_dir(self) -> str:
        return (
            self.get_cache("output_dir", None)
            or os.getenv("SP_OUTPUT_DIR", None)
            or f"{os.getcwd()}/{SP_LABEL.lower()}_output"
        )
