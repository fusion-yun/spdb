import tempfile
import shutil
import pathlib
import os
import typing
import contextlib

from spdm.utils.logger import logger
from spdm.utils.envs import SP_DEBUG, SP_LABEL

from spdm.core.path import Path
from spdm.core.sp_tree import sp_property, SpTree
from spdm.core.domain import WithDomain
from spdm.core.time import WithTime

from spdm.model.port import Ports
from spdm.model.entity import Entity


class Actor(SpTree):
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

    in_ports: Ports
    """输入的 Edge，记录对其他 Actor 的依赖。"""

    @property
    def context(self) -> typing.Self:
        """获取当前 Actor 所在的 Context。"""
        return getattr(self._parent, "context", None)

    def initialize(self, *args, **kwargs) -> None:
        """初始化 Actor 。"""
        self.in_ports.connect(self.context)

    def advance(self, *args, **kwargs) -> typing.Self:
        """推进到下一个时间片，时间为 time"""
        return super().advance(*args, **kwargs)

    def refresh(self, *args, **kwargs) -> typing.Self:
        """更新当前时间片 （time_slice）"""
        return super().refresh(*args, **kwargs)

    def fetch(self, *args, **kwargs) -> typing.Self:
        """返回在 time, domain 上的 _TSlice，默认返回 time_slice.current
        projection: 投影函数，从数据集_TSlice中选择一部分字段操作
        """
        return super().fetch(*args, **kwargs)

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
