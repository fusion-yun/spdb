import tempfile
import shutil
import pathlib
import os
import typing
import contextlib


from spdm.utils.logger import logger
from spdm.utils.envs import SP_DEBUG, SP_LABEL


class Worker:
    """用于管理运行环境"""

    pass


class LocalWorker(Worker):

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
            self.get("output_dir", None)
            or os.getenv("SP_OUTPUT_DIR", None)
            or f"{os.getcwd()}/{SP_LABEL.lower()}_output"
        )
