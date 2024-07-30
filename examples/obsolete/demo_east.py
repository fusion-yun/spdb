
import sys
sys.path.append("/home/salmon/workspace/freegs/")
sys.path.append("/home/salmon/workspace/fytok/python")
sys.path.append("/home/salmon/workspace/SpDev/SpDB")


if __name__ == '__main__':
    from ..util.logger import logger
    from spdm.core.entry import open_entry

    entry = open_entry("east+mdsplus:///home/salmon/public_data/~t/?tree_name=efit_east", shot=55555, time_slice=10)

    # logger.debug(entry.pf_active.coil[1].element[0].geometry.rectangle.r())
    # logger.debug(entry.wall.description_2d[0].limiter.unit[0].outline.r())
    # logger.debug(entry.wall.description_2d[0].limiter.unit[0].outline.r())

    logger.debug(entry.equilibrium.vacuum_toroidal_field())
    logger.debug(entry.equilibrium.vacuum_toroidal_field.b0())
    # logger.debug(entry.equilibrium.profiles_1d())
    # logger.debug(entry.equilibrium.profiles_1d.dpressure_dpsi())
