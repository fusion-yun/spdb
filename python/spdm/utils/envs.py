import os

SP_DEBUG = os.environ.get("SP_DEBUG", True)

SP_VERBOSE = os.environ.get("SP_VERBOSE", "info")

if SP_DEBUG in (True, "true", "on"):
    SP_VERBOSE = "debug"


SP_LABEL = os.environ.get("SP_LABEL", __package__[: __package__.find(".")])

SP_MPI = None
SP_MPI_RANK = 0
SP_MPI_SIZE = 0
if int(os.environ.get("OMPI_COMM_WORLD_SIZE", "0")) > 0:
    try:
        from mpi4py import MPI as SP_MPI

        SP_MPI_RANK = SP_MPI.COMM_WORLD.Get_rank()
        SP_MPI_SIZE = SP_MPI.COMM_WORLD.Get_size()
    except ImportError:
        pass
try:
    from ..__version__ import __version__
except ImportError:
    SP_VERSION = "develop"
else:
    SP_VERSION = __version__


def is_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter
