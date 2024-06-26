import pathlib
from spdm.core.file import File
from spdm.utils.logger import logger

WORKSPACE = "/home/salmon/workspace"  # "/ssd01/salmon_work/workspace/"

DATA_PATH = pathlib.Path(f"{WORKSPACE}/fytok_data/data")

if __name__ == '__main__':

    with File(DATA_PATH/"g063982.04800", mode="r", scheme="GEQdsk") as fid:
        doc = fid.read()
        eq = doc.dump()

    with File("../output/test.gfile", mode="w", scheme="GEQdsk") as oid:
        oid.write(eq)

    with File("../output/test.json", mode="w") as oid:
        oid.write(eq)

    with File("../output/test.json", mode="r") as oid:
        logger.debug(oid.read().dump())

    with File("../output/test.yaml", mode="w") as oid:
        oid.write(eq)

    with File("../output/test.yaml", mode="r") as oid:
        logger.debug(oid.read().dump())

    with File("../output/test.h5", mode="w", scheme="HDF5") as oid:
        oid.write(eq)

    with File("../output/test.h5", mode="r", scheme="HDF5") as oid:
        logger.debug(oid.read().dump())

    with File("../output/test.nc", mode="w", scheme="NetCDF") as oid:
        oid.write(eq)

    with File("../output/test.nc", mode="r", scheme="NetCDF") as oid:
        logger.debug(oid.read().dump())

    # with open("../output/test.json", mode="w") as fp:
    #     d = doc.dump(enable_ndarray=False)
    #     json.dump(d, fp)
