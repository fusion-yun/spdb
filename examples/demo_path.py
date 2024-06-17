from spdm.core.path import Path
from spdm.utils.logger import logger


if __name__ == '__main__':
    logger.debug(Path.parser("/a[@a='hello']/b/c"))
