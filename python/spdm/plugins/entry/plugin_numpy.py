import collections
import json

import numpy as np
from spdm.utils.logger import logger

from spdm.core.collection import FileCollection
from spdm.core.document import Document


class NumpyEncoder(json.NumPyEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()

        logger.debug(type(obj))
        return super().default(obj)


class NumPyDocument(Document):
    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        self._path = path

    def load(self, *args, path=None,  **kwargs):
        with open(path or self._path, mode="r") as fid:
            self.root._holder = np.load(fid)

    def save(self,   *args, path=None, **kwargs):
        with open(path or self._path, mode="w") as fid:
            np.save(fid, self.root._holder)


class NumPyCollection(FileCollection):
    def __init__(self, uri, *args, **kwargs):
        super().__init__(uri, *args,
                         file_extension=".json",
                         file_factory=lambda *a, **k: NumPyDocument(*a, **k),
                         ** kwargs)
