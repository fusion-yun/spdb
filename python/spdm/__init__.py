__path__ = __import__('pkgutil').extend_path(__path__, __name__)

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("spdb")
except PackageNotFoundError:
    __version__ = "unknown version"
