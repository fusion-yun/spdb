import pprint
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy import constants  


if __name__ == "__main__":

    sys.path.append("/home/salmon/workspace/SpDev/SpDB")

    from spdm.core.file import File
    from ..util.logger import logger

    fp = File("/home/salmon/workspace/SpDev/SpDB/examples/data/FuYun/modules/physics/genray/template/g063982.04800",
              metadata={"$schema": "file/geqdsk"})

    logger.debug(fp)
