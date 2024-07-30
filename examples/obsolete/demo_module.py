
import os

from spdm.core.file import File
from spdm.flow.ModuleRepository import ModuleRepository
from spdm.flow.SpModule import SpModule
from ..util.logger import logger
import pprint

if __name__ == "__main__":

    logger.info("====== START =======")

    module = ModuleRepository(repo_name='FuYun', repo_tag='FY')

    module.load_configure("/home/salmon/workspace/fytok/external/SpDB/examples/data/FuYun/configure.yaml")

    os.environ["SP_OUTPUT_DIR"] = "/home/salmon/workspace/output"

    module.build("physics/cql3d")

    # CQL3D = module.new_class("physics/cql3d")

    # Genray = module.new_class("physics/genray", version="10.13_200117", tag="-gompi-2020a")

    # logger.debug(pprint.pformat((CQL3D._metadata)))

    # logger.debug(pprint.pformat((Genray._metadata)))

    # cfg = {
    #     "$schema": "file/namelist",
    #     "default": {
    #         "tokamak": {
    #             # {"$class": "file.geqdsk", "path": "{FY_MODULEFILE_DIR}/template/g063982.04800"},
    #             "eqdskin": "{equilibrium}"
    #         },
    #         "genr": {
    #             "partner":  {"$class": "file.netcdf", "path": "/home/salmon/workspace/data/genray/genray_profs_in.nc"},
    #             "outdat": "{WORKING_DIR}"
    #         },
    #         "ecocone": {"gzone": 1}
    #     }
    # }
    # equilibrium = File("/home/salmon/workspace/fytok/external/SpDB/examples/data/FuYun/modules/physics/genray/10.13_200117-gompi-2020a/template/g063982.04800",
    #                   format="geqdsk")

    # genray = Genray(num_of_steps=1, dt=0.001, equilibrium=equilibrium,  config=cfg)

    # logger.debug(genray.outputs.EXITCODE)

    # cql3d = CQL3D(equilibrium=genray.outputs.equilibrium, ray_trace=genray.outputs.result)

    # logger.debug(cql3d.outputs.EXITCODE)

    # out_nc = genray_out.out_nc
    # out_eq = genray_out.out_eq

    # wr = out_nc.entry.wr[1]/100.0
    # wz = out_nc.entry.wz[:]/100.0

    # plt.plot(out_eq.limrz[:, 0], out_eq.limrz[:, 1])
    # plt.plot(out_eq.bbsrz[:, 0], out_eq.bbsrz[:, 1])

    # plt.plot(wr, wz)
    # plt.contour(
    #     out_nc.eqdsk_r[:, :],
    #     out_nc.eqdsk_z[:, :],
    #     out_nc.eqdsk_psi[:, :])

    # plt.savefig("../output/demo_module.svg")

    logger.info("====== Done =======")
