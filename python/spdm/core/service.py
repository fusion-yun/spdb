"""This module contains the definition of the Service class and its subclass ServiceBundle.

The Service class is a service object that encapsulates business logic related to specific domain operations.
A Service typically consists of one or more operations (methods) that perform complex tasks spanning multiple domain objects.

The Service class is stateless and follows interface programming principles.

The ServiceBundle class is a subclass of Service and represents a bundle of services.
"""

from __future__ import annotations
import tempfile
import shutil
import pathlib
import os
import typing
import contextlib

from spdm.utils.logger import logger
from spdm.utils.envs import SP_DEBUG, SP_LABEL

from spdm.core.htree import HTreeNode
from spdm.core.port import Ports, Port
from spdm.core.path import Path
from spdm.core.pluggable import Pluggable


class Service(Pluggable):
    """
    Service is a service object that encapsulates business logic related to specific domain operations.
    A Service typically consists of one or more operations (methods) that perform complex tasks spanning multiple domain objects.

    The Service class is stateless and follows interface programming principles.
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

        self._inports = Ports(inputs, _parent=self)
        self._outports = Ports(_parent=self)

    @property
    def inports(self) -> Ports:
        """Returns the input edges that record dependencies on other actors."""
        return self._inports

    @property
    def outports(self) -> Ports:
        """Returns the output edges that can be considered as references."""
        return self._outports

    @contextlib.contextmanager
    def working_dir(self, suffix: str = "", prefix="") -> typing.Generator[pathlib.Path, None, None]:
        """Context manager that changes the working directory to a temporary directory or a specified directory.

        Args:
            suffix (str): The suffix to be appended to the directory name.
            prefix (str): The prefix to be prepended to the directory name.

        Yields:
            pathlib.Path: The current working directory.

        """
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
        """Returns the output directory path.

        Returns:
            str: The output directory path.

        """
        return (
            self.get_cache("output_dir", None)
            or os.getenv("SP_OUTPUT_DIR", None)
            or f"{os.getcwd()}/{SP_LABEL.lower()}_output"
        )

    def initialize(self, *args, **kwargs) -> None:
        """Initializes the actor."""
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
            # Look for input from parent node and update the link Port
            if k.isidentifier() and p.node is None:
                p.update(Path(k).get(ctx, None))

            if p.node is None:
                logger.warning(f"Input {k} is not provided! context = {ctx}")

    def preprocess(self, *args, **kwargs) -> typing.Type[StateTree]:
        """Preprocesses the actor and updates its state tree if necessary.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            typing.Type[StateTree]: The current state tree.

        """
        for k in [*kwargs.keys()]:
            if isinstance(kwargs[k], HTreeNode):
                self.inports[k] = kwargs.pop(k)

        current = self.time_slice.current

        return current

    def execute(self, current: typing.Type[StateTree], *args) -> typing.Type[StateTree]:
        """Updates the current time slice based on inports and the previous time slice.

        Args:
            current (typing.Type[StateTree]): The current state tree.
            *args: Positional arguments.

        Returns:
            typing.Type[StateTree]: The updated state tree.

        """
        return current

    def postprocess(self, current: typing.Type[StateTree]) -> typing.Type[StateTree]:
        """Postprocesses the actor and updates its state tree if necessary.

        Args:
            current (typing.Type[StateTree]): The current state tree.

        Returns:
            typing.Type[StateTree]: The updated state tree.

        """
        return current

    def refresh(self, *args, **kwargs) -> typing.Type[StateTree]:
        """Updates the current state of the actor.

        Returns:
            typing.Type[StateTree]: The updated state tree.

        """
        current = self.preprocess(*args, **kwargs)

        current = self.execute(current, self.time_slice.previous)

        current = self.postprocess(current)

        return current

    def flush(self) -> None:
        """Saves the state of the current time slice.

        Returns:
            None

        """
        return self.time_slice.flush()

    def finalize(self) -> None:
        """Finalizes the actor.

        Returns:
            None

        """
        self.flush()
        self.time_slice.finalize()

    def fetch(self, *args, **kwargs) -> typing.Type[StateTree]:
        """Returns a time slice description based on the current state and the given parameters.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            typing.Type[StateTree]: The time slice description.

        """
        return HTreeNode._do_fetch(self.time_slice.current, *args, **kwargs)


class ServiceBundle(Service):
    """A bundle of services."""

    def __init__(self, *args, **kwargs):
        self._bundle = []
