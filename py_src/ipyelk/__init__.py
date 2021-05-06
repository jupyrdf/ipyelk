# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ._version import __version__
from .diagram import Diagram, Viewer
from .loaders import from_elkjson, from_nx
from .pipes import Pipe, Pipeline


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@jupyrdf/jupyter-elk"}]


__all__ = [
    "__version__",
    "Diagram",
    "Viewer",
    "Pipe",
    "Pipeline",
    "from_nx",
    "from_elkjson",
]
