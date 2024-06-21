from spdm.utils.tree_utils import update_tree
from spdm.utils.logger import logger
import pprint
if __name__ == "__main__":

    d = update_tree(None, "a/b/c/1/2/c", "hello")

    pprint.pprint(d)

    update_tree(d, "a/b/d", {"hello": [1, 2, 3, 4, 5]})

    pprint.pprint(d)

    update_tree(d, None, {"a/b/d/hello": 789})

    pprint.pprint(d)
