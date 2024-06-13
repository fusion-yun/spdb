from __future__ import annotations
import tempfile
import shutil
import pathlib
import os
import typing
import contextlib

from ..utils.logger import logger
from ..utils.envs import SP_DEBUG, SP_LABEL
from ..utils.tags import _not_found_

from .htree import HTreeNode
from .edge import InPorts, OutPorts, Port
from .path import Path
from .obsolete.sp_tree import sp_property, sp_tree
from .pluggable import Pluggable


class Service(Pluggable):
    """
    Service是一种服务对象,它封装了一些与特定领域操作相关的业务逻辑。
    Service通常由一个或多个操作(方法)组成,这些操作执行一些比较复杂、跨多个领域对象的任务。

    Service 无状态, 面向接口编程:
    """

    def __new__(cls, *args, **kwargs) -> typing.Type[typing.Self]:

        cls_name = args[0].get("$class", None) if len(args) == 1 and isinstance(args[0], dict) else None

        return super().__new__(cls, cls_name)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        inputs = {}
        tp_hints = typing.get_type_hints(self.__class__.refresh)
        for name, tp in tp_hints.items():
            if name == "return":
                continue
            elif getattr(tp, "_name", None) == "Optional":  # check typing.Optional
                t_args = typing.get_args(tp)
                if len(t_args) == 2 and t_args[1] is type(None):
                    tp = t_args[0]

            inputs[name] = Port(None, type_hint=tp)

        self._inports = InPorts(inputs, _parent=self)
        self._outports = OutPorts(_parent=self)

    @property
    def inports(self) -> InPorts:
        """输入的 Edge，记录对其他 Actor 的依赖。"""
        return self._inports

    @property
    def outports(self) -> OutPorts:
        """输出的 Edge，可视为对于引用（reference）的记录"""
        return self._outports

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
        except Exception as error:
            if temp_dir is not None:
                shutil.copytree(temp_dir.name, working_dir, dirs_exist_ok=True)
            os.chdir(pwd)
            logger.info(f"Enter directory {pwd}")
            logger.exception(f"Failed to execute actor {self.tag}! \n See log in {working_dir} ")
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

    def initialize(self, *args, **kwargs) -> None:
        """初始化 Actor 。"""
        if self.time_slice.is_initializied:
            return

        self.time_slice.initialize(*args, **kwargs)

        from .context import Context

        ctx = self

        while ctx is not None:
            if isinstance(ctx, Context):
                break
            else:
                ctx = getattr(ctx, "_parent", None)

        for k, p in self._inports.items():
            # 查找父节点的输入 ，更新链接 Port
            if k.isidentifier() and p.node is None:
                p.update(Path(k).get(ctx, None))

            if p.node is None:
                logger.warning(f"Input {k} is not provided! context = {ctx}")

    def preprocess(self, *args, **kwargs) -> typing.Type[StateTree]:
        """Actor 的预处理，若需要，可以在此处更新 Actor 的状态树。"""

        for k in [*kwargs.keys()]:
            if isinstance(kwargs[k], HTreeNode):
                self.inports[k] = kwargs.pop(k)

        # inputs = {k: kwargs.pop(k) for k in [*kwargs.keys()] if isinstance(kwargs[k], HTreeNode)}
        # self.inports.update(inputs)

        current = self.time_slice.current
        # current.refresh(*args, **kwargs)

        return current

    def execute(self, current: typing.Type[StateTree], *args) -> typing.Type[StateTree]:
        """根据 inports 和 前序 time slice 更新当前time slice"""
        return current

    def postprocess(self, current: typing.Type[StateTree]) -> typing.Type[StateTree]:
        """Actor 的后处理，若需要，可以在此处更新 Actor 的状态树。
        @param current: 当前时间片
        @param working_dir: 工作目录
        """
        return current

    def refresh(self, *args, **kwargs) -> typing.Type[StateTree]:
        """更新当前 Actor 的状态。
        更新当前状态树 （time_slice），并执行 self.iteration+=1

        """

        current = self.preprocess(*args, **kwargs)

        current = self.execute(current, self.time_slice.previous)

        current = self.postprocess(current)

        return current

    def flush(self) -> None:
        """保存当前时间片的状态。
        根据当前 inports 的状态，更新状态并写入 time_slice，
        默认 do nothing， 返回当前时间片
        """
        return self.time_slice.flush()

    def finalize(self) -> None:
        """完成。"""

        self.flush()
        self.time_slice.finalize()

    def fetch(self, *args, **kwargs) -> typing.Type[StateTree]:
        """根据当前状态，根据参数返回一个时间片描述。
        例如，根据给定的坐标，对 object 进行插值，构建相应的时间片。
        """
        return HTreeNode._do_fetch(self.time_slice.current, *args, **kwargs)


class ServiceBundle(Service):
    def __init__(self, *args, **kwargs):

        self._bundle = []
