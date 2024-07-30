import pprint
import matplotlib.pyplot as plt
import numpy as np
import pathlib
from spdm.core.file import File
from ..util.logger import logger
import sys


if __name__ == '__main__':
    doc = File(pathlib.Path(__file__).parent/"data/g063982.04800", format="GEQdsk")
    pprint.pprint(doc.root._holder)
