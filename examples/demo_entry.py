import os
import pathlib
from spdm.core.file import File
from spdm.core.entry import open_entry
from spdm.utils.logger import logger

WORKSPACE = "/home/salmon/workspace"  # "/ssd01/salmon_work/workspace/"
OUTPUT_PATH = f"{WORKSPACE}/output"

os.environ["SP_DATA_MAPPING_PATH"] = f"{WORKSPACE}/fytok_data/mapping"


if __name__ == '__main__':

    DATA_PATH = pathlib.Path(f"{WORKSPACE}/fytok_data/gfiles")

    # eq0 = open_entry(f"file+geqdsk:///{DATA_PATH.as_posix()}/g063982.04800", mode="r").fetch()

    # eq1 = open_entry(DATA_PATH/"g063982.04800", mode="r", format="geqdsk").fetch()

    # logger.debug(eq0)

    # logger.debug(eq1)

    # eq2 = open_entry(f"east+mdsplus://{WORKSPACE}/fytok_data/mdsplus/~t/?enable=efit_east", shot=70745)

    # # eq2 = open_entry(f"east+mdsplus://202.127.204.12", shot=70745)

    # logger.debug(eq2.child("equilibrium/time_slice/0/boundary/outline/r").fetch())

    # eq3 = open_entry(f"cfetr")

    # logger.debug(eq3.child("wall/description_2d/0/limiter/unit/0/outline/r").fetch())

    shot_num = 70754

    time_slice = 10

    entry = open_entry(f"east+mdsplus://202.127.204.12?enable=efit_east&shot={shot_num}")

    data = {
        "wall": entry.child(f"wall"),
        "equilibrium": {"time_slice": [entry.child(f"equilibrium/time_slice/{time_slice}")]}
    }

    with File(f"{OUTPUT_PATH}/g{shot_num}.gfile", mode="w", scheme="geqdsk") as fid:
        fid.write(data, description="equilibrium")
