import pprint
import sys
import unittest

import numpy as np
import scipy.integrate
from spdm.utils.RefResolver import RefResolver

sys.path.append("/home/salmon/workspace/SpDev/SpDB")

npoints = 129


class TestRefResolver(unittest.TestCase):

    def test_validate(self):
        resolver = RefResolver(
            base_uri="https://fusionyun.org/schema/draft-00",
            prefetch="pkgdata://spdm/schemas/",
            alias=[["*",   "/home/salmon/workspace/SpDev/SpDB/examples/data/FuYun/modules/*/fy_module.yaml", ],
                   ["*", "/fuyun/modules/*/fy_module.yaml"]])

        logger.debug(resolver.fetch("physics/genray/201213-gompi-2019b"))


if __name__ == '__main__':
    from spdm.utils.logger import logger
    from spdm.utils.RefResolver import RefResolver

    unittest.main()
