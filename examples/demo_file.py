import pathlib
from spdm.core.file import File
from spdm.utils.logger import logger

WORKSPACE = "/home/salmon/workspace"  # "/ssd01/salmon_work/workspace/"

DATA_PATH = pathlib.Path(f"{WORKSPACE}/fytok_data/data")

if __name__ == '__main__':

    with File(DATA_PATH/"g063982.04800", mode="r", format="GEQdsk") as fid:
        doc = fid.read()
        eq = doc.dump()

    with File("../output/test.gfile", mode="w", format="GEQdsk") as oid:
        oid.write(eq)

    with File("../output/test.json", mode="w") as oid:
        oid.write(eq)

    with File("../output/test.json", mode="r") as oid:
        logger.debug(oid.read().dump())

    with File("../output/test.yaml", mode="w") as oid:
        oid.write(eq)

    with File("../output/test.yaml", mode="r") as oid:
        logger.debug(oid.read().dump())

    with File("../output/test.h5", mode="w", format="HDF5") as oid:
        oid.write(eq)

    with File("../output/test.h5", mode="r", format="HDF5") as oid:
        logger.debug(oid.read().dump())

    with File("../output/test.nc", mode="w", format="NetCDF") as oid:
        oid.write(eq)

    with File("../output/test.nc", mode="r", format="NetCDF") as oid:
        logger.debug(oid.read().dump())

    # with open("../output/test.json", mode="w") as fp:
    #     d = doc.dump(enable_ndarray=False)
    #     json.dump(d, fp)
