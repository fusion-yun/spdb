import unittest
from copy import deepcopy

from spdm.utils.tags import _not_found_
from spdm.view.View import display
from spdm.utils.logger import logger
from spdm.geometry.Circle import Circle


class TestView(unittest.TestCase):
    def test_display(self):
        c = Circle(0, 0, 1)
        logger.debug(display(c))


if __name__ == '__main__':
    unittest.main()
