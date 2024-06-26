import pathlib
from spdm.core.file import File
from spdm.utils.logger import logger

WORKSPACE = "/home/salmon/workspace"  # "/ssd01/salmon_work/workspace/"

DATA_PATH = pathlib.Path(f"{WORKSPACE}/fytok_data/data")

if __name__ == '__main__':

    with File("/home/salmon/workspace/gacode/neo/tools/input/profile_data/iterdb141459.03890", mode="r", scheme="iterdb") as fid:
        doc = fid.read()
        eq = doc.dump()

    logger.debug(eq)
