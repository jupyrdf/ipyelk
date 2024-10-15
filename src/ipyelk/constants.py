# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

try:
    from importlib.metadata import version
except:
    from importlib_metadata import version

NAME = "ipyelk"

__version__ = version(NAME)

EXTENSION_NAME = "@jupyrdf/jupyter-elk"
EXTENSION_SPEC_VERSION = (
    __version__.replace("a", "-alpha").replace("b", "-beta").replace("rc", "-rc")
)

__all__ = ["EXTENSION_NAME", "EXTENSION_SPEC_VERSION", "__version__"]
