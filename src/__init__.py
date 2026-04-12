"""Source code of your project."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("Chess Analyzer")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"  # updated by semantic-release
