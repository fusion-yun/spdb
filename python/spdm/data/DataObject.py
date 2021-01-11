import collections
import pathlib
import pprint
import os
import numpy as np
from spdm.util.AttributeTree import AttributeTree
from spdm.util.logger import logger
from spdm.util.sp_export import sp_find_module
from spdm.util.SpObject import SpObject


from .Node import Node


def load_ndarray(desc, value, *args, **kwargs):
    if isinstance(value, np.ndarray):
        return value
    else:
        return NotImplemented


class DataObject(SpObject):

    associations = {
        "general": ".data.General",
        "integer": int,
        "float": float,
        "string": str,
        "ndarray": np.ndarray,


        "file.table": ".data.file.Table",
        "file.bin": "Binary",
        "file.h5": ".data.file.HDF5",
        "file.hdf5": ".data.file.HDF5",
        "file.nc": ".data.file.netCDF",
        "file.netcdf": ".data.file.netCDF",
        "file.namelist": ".data.file.namelist",
        "file.nml": ".data.file.namelist",
        "file.xml": ".data.file.XML",
        "file.json":  ".data.file.JSON",
        "file.yaml": ".data.file.YAML",
        "file.txt": ".data.file.TXT",
        "file.csv": ".data.file.CSV",
        "file.numpy": ".data.file.NumPy",
        "file.geqdsk": ".data.file.GEQdsk",
        "file.gfile": ".data.file.GEQdsk",
        "file.mds": ".data.db.MDSplus#MDSplusDocument",
        "file.mdsplus": ".data.db.MDSplus#MDSplusDocument",

        # "file": ".data.File",
        # "file.general": ".data.file.GeneralFile",
        # "file.bin": ".data.file.Binary",
        # "file.hdf5": ".data.file.HDF5",
        # "file.netcdf": ".data.file.netCDF",
        # "file.namelist": ".data.file.namelist",
        # "file.xml": ".data.file.XML",
        # "file.json": ".data.file.JSON",
        # "file.yaml": ".data.file.YAML",
        # "file.txt": ".data.file.TXT",
        # "file.csv": ".data.file.CSV",
        # "file.numpy": ".data.file.NumPy",
        # "file.geqdsk": ".data.file.GEQdsk",
        # "file.mdsplus": ".data.db.MDSplus#MDSplusDocument",
    }

    def __new__(cls,   _metadata=None, *args, **kwargs):
        if cls is not DataObject and _metadata is None:
            return SpObject.__new__(cls)

        if isinstance(_metadata, str):
            n_cls = _metadata
            _metadata = {"$class": n_cls}
        elif isinstance(_metadata, collections.abc.Mapping):
            n_cls = _metadata.get("$class", "general")
        else:
            n_cls = cls

        if isinstance(n_cls, str):
            n_cls = n_cls.replace("/", ".")
            if n_cls[0] != '.':
                n_cls = DataObject.associations.get(n_cls.lower(), None)
            _metadata = collections.ChainMap({"$class": n_cls}, _metadata)

        return SpObject.__new__(cls, _metadata, *args, **kwargs)

    def __init__(self, _metadata=None, *args,  **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def serialize(self, *args, **kwargs):
        return super().serialize(*args, **kwargs)

    @ classmethod
    def deserialize(cls, *args, **kwargs):
        return super().deserialize(cls, *args, **kwargs)

    @ property
    def root(self):
        return Node(self)

    @ property
    def entry(self):
        return self.root.entry

    @ property
    def value(self):
        return NotImplemented

    def update(self, value):
        raise NotImplementedError