import matplotlib.pyplot as plt
from fytok.transport.Equilibrium import Equilibrium
from spdm.core.file import File
import numpy as np
from ..util.logger import logger

if __name__ == "__main__":

    eqdsk = File(
        # "/home/salmon/workspace/fytok/examples/data/NF-076026/geqdsk_550s_partbench_case1",
        "/home/salmon/workspace/data/15MA inductive - burn/Standard domain R-Z/High resolution - 257x513/g900003.00230_ITER_15MA_eqdsk16HR.txt",
        # "/home/salmon/workspace/data/Limiter plasmas-7.5MA li=1.1/Limiter plasmas 7.5MA-EQDSK/Limiter_7.5MA_outbord.EQDSK",
        format="geqdsk")

    equilibrium = Equilibrium({"time": 0.0,
                               "time_slice": {
                                   "profiles_1d": eqdsk.entry.pull("profiles_1d"),
                                   "profiles_2d": eqdsk.entry.pull("profiles_2d"),
                                   "coordinate_system": {"Mesh": {"dim1": 100, "dim2": 256}}
                               },
                               "vacuum_toroidal_field":  eqdsk.entry.pull("vacuum_toroidal_field"),
                               })

    o_points, x_points = equilibrium.coordinate_system.critical_points
    psi_axis = o_points[0].psi
    psi_bdry = x_points[0].psi
    psi = np.linspace(psi_axis, psi_bdry, 16)
    # psirz = equilibrium.coordinate_system._psirz
    # data = psirz.__array__()
    # R, Z = psirz.mesh.points
    # logger.debug(type(data))
    contour_set = equilibrium.coordinate_system.find_surface(psi)

    fig = plt.figure()
    # contour_set = plt.contour(R, Z, data, levels=np.linspace(psi_axis, psi_bdry, 16))
    for curv in contour_set:
        if curv is not None:
            plt.plot(*curv.xy.T)

    fig.savefig("/home/salmon/workspace/output/contour.svg", transparent=True)
    # logger.debug(len(contours))
