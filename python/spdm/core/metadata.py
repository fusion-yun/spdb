from copy import deepcopy

from spdm.core.path import Path


class Metadata:
    """在创建子类时候，添加 metadata 作为类变量"""

    _metadata = {}

    def __init_subclass__(cls, **metadata):
        if len(metadata) > 0:
            cls._metadata = Path().update(deepcopy(cls._metadata), metadata)

        super().__init_subclass__()
