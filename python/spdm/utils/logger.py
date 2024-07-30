import atexit
import collections.abc
import inspect
import os

import pathlib
import pprint
import sys
from datetime import datetime
from inspect import getframeinfo, stack


import logging
import logging.handlers


from .envs import SP_VERBOSE, SP_DEBUG, SP_MPI, SP_LABEL, SP_MPI_RANK, SP_MPI_SIZE

default_formater = logging.Formatter(
    "%(asctime)s [%(name)8s] %(levelname)8s:" "%(pathname)s:%(lineno)d:%(funcName)s: " "%(message)s"
)


MPI_MSG = ""

if SP_MPI is not None and SP_MPI_RANK > 0:
    MPI_MSG = f"[{SP_MPI_RANK}/{SP_MPI_SIZE}]"

logging.VERBOSE = int((logging.INFO + logging.DEBUG) / 2)
logging.addLevelName(logging.VERBOSE, "VERBOSE")


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    # Black       0;30     Dark Gray     1;30
    # Blue        0;34     Light Blue    1;34
    # Green       0;32     Light Green   1;32
    # Cyan        0;36     Light Cyan    1;36
    # Red         0;31     Light Red     1;31
    # Purple      0;35     Light Purple  1;35
    # Brown       0;33     Yellow        1;33
    # Light Gray  0;37     White         1;37

    grey = "\x1b[0;37m"
    blue = "\x1b[0;34m"
    yellow = "\x1b[1;33m"
    brown = "\x1b[0;33m"
    green = "\x1b[0;32m"
    red = "\x1b[0;31m"
    bold_red = "\x1b[1;31m"
    reset = "\x1b[0m"

    format_normal = (
        "%(asctime)s [%(name)8s] %(levelname)8s:" + MPI_MSG + " %(pathname)s:%(lineno)d:%(funcName)s: %(message)s"
    )

    FORMATS = {
        logging.DEBUG: grey + format_normal + reset,
        logging.VERBOSE: grey + "%(asctime)s [%(name)8s] %(levelname)8s: " + MPI_MSG + "%(message)s" + reset,
        logging.INFO: blue + "%(asctime)s [%(name)8s] %(levelname)8s: " + MPI_MSG + "%(message)s" + reset,
        logging.WARNING: brown + format_normal + reset,
        logging.ERROR: red + format_normal + reset,
        logging.CRITICAL: bold_red + format_normal + reset,
    }

    def format(self, record: logging.LogRecord):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        if isinstance(record.msg, collections.abc.Mapping):
            record.msg = pprint.pformat(record.msg)
        return formatter.format(record)


class SpLogger(logging.Logger):

    def verbose(self, msg, *args, **kwargs):
        # 继承 logging.Logger ， logging.Logger.findCaller 无法正确找到调用函数位置
        if self.isEnabledFor(logging.VERBOSE):
            self._log(logging.VERBOSE, msg, args, **kwargs)


logging.setLoggerClass(SpLogger)


def sp_enable_logging(name, /, handler=None, prefix=None, formater=None):

    m_logger = logging.getLogger(name)

    formater = formater or CustomFormatter()

    if isinstance(handler, str) and handler == "STDOUT":
        handler = logging.StreamHandler(stream=sys.stdout)
    elif handler is None:
        prefix = prefix or os.environ.get("SP_LOG_PREFIX", f"/tmp/sp_log_{os.environ['USER']}/sp_")
        path = pathlib.Path(f"{prefix}{datetime.now().strftime(r'%Y%m%d_%H%M%S')}.log")
        path = path.expanduser().resolve()
        if not path.parent.exists():
            path.parent.mkdir(mode=0o0755, exist_ok=True)
        handler = logging.FileHandler(path)

    if issubclass(type(handler), logging.Handler):
        handler.setFormatter(formater or default_formater)
        handler.setLevel(logging.DEBUG)
        m_logger.addHandler(handler)
    else:
        raise NotImplementedError()

    match SP_VERBOSE:
        case "50" | 50 | "quiet" | "critical" | "fatal" | "false" | "False" | False:
            level = logging.CRITICAL
        case "40" | "true" | "error" | True:
            level = logging.ERROR
        case "30" | "warning":
            level = logging.WARNING
        case "20" | "info":
            level = logging.INFO
        case "15" | "verbose":
            level = logging.VERBOSE
        case _:
            level = logging.DEBUG

    if SP_MPI_RANK == 0:
        m_logger.setLevel(level)
    else:
        m_logger.setLevel(logging.ERROR)

    return m_logger


logger = sp_enable_logging(SP_LABEL, handler="STDOUT")


def _at_end():
    logger.setLevel(logging.INFO)
    logger.info("The End")
    logging.shutdown()


atexit.register(_at_end)


def deprecated(func):
    """python 修饰器，作用于类方法或函数，当函数或方法被调用时，在标准日志输出 函数或方法定义所在文件和行数"""

    def _wrap(func):
        def wrapped(*args, __fun__=func, **kwargs):
            caller = getframeinfo(stack()[1][0])
            file_name = caller.filename
            line_number = caller.lineno

            if inspect.isfunction(func):
                logger.info(f"Calling deprecated function {file_name}:{line_number}:'{__fun__.__qualname__}' !")
            else:
                logger.info(f"Calling deprecated function {file_name}:{line_number}:{__fun__.__name__}")

            return __fun__(*args, **kwargs)

        return wrapped

    if isinstance(func, str):
        logger.warning(func)
        return lambda o: _wrap(func)
    else:
        return _wrap(func)


def experimental(func):
    def _wrap(func):
        def wrapped(*args, __fun__=func, **kwargs):
            if inspect.isfunction(func):
                logger.warning(f"Experimental function '{__fun__.__qualname__}' !")
                raise DeprecationWarning(__fun__.__qualname__)
            else:
                logger.warning(f"Experimental object {__fun__}")
            return __fun__(*args, **kwargs)

        return wrapped

    if func is None:
        return lambda o: _wrap(func)
    else:
        return _wrap(func)


__all__ = ["logger", "deprecated", "experimental"]
