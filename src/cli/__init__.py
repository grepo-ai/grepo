from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("grepo")
except PackageNotFoundError:
    __version__ = "not found"
