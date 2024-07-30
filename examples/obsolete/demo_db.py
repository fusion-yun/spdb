import os

from spdm.utils.logger import logger
from spdm.core.entry import open_db


os.environ["SP_DATA_MAPPING_PATH"] = "/home/salmon/workspace/fytok_data/mapping"

if __name__ == '__main__':

    # db = open_db("mdsplus[EAST]:///home/salmon/workspace/data/~t/?tree_name=efit_east")

    # entry = db.find_one(38300)

    # logger.debug(entry.get(["pf_active"]).dump())

    db = open_db("MDSplus[EAST]://202.127.204.12?tree_name=efit_east")

    entry = db.find_one(114730)

    logger.debug(entry.child("pf_active").__value__())
