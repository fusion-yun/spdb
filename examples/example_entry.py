import os

from spdm.core.entry import open_entry
from spdm.core.file import File

import matplotlib.pyplot as plt
from sptask import EQTASK


if __name__ == '__main__':
    # open entry for structure data and smi -structure data
    entry_db = open_entry("EAST://127.0.0.1#38300")

    # get pf,mag ,and wall
    wall = entry_db.child("wall")
    pf_active = entry_db.child("pf_active")
    magnetics = entry_db.child("magnetics")

    # open entry2 for non-structure data gdskfile ,which come from other simulation code.
    entry_file = open_entry("/<input path>/38300.gfile", format="GEqdsk", mode="r")

    time_slice = 50

    eq = entry_file.child("equilibrium/time_slice/{time_slice}")

    # Combine multiple IDSs into input_entry
    input_entry = {
        "wall": wall,
        "pf_active": pf_active,
        "magnetics": magnetics,
        "equilibrium": eq
    }

    # same entry to different eq code ,and unifie API GQTASK to call different eq code.

    # run the EQTASK to update out for eq_ids

    # Combine the new eq_ids and the unchanged device data into out_entry for the next step.

    task_1 = EQTASK(input_entry, id="freegs")

    result_1 = task_1.run()

    with File("/<output path>/38300_out.h5", mode="w") as fid:
        # open new entry to write IDS dict to hdf5 file
        fid.write(result_1)

    # plot the result directly

    task_2 = EQTASK(input_entry, id="atec")

    result_2 = task_2.run()

    plt.contour(result_2.get("time_slice/-1/profiles_2d/0/psi"))
