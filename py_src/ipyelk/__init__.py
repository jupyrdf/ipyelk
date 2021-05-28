# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ._version import __version__
from .diagram import Diagram, Viewer
from .loaders import (
    ElementLoader,
    ElkJSONLoader,
    Loader,
    NXLoader,
    from_element,
    from_elkjson,
    from_nx,
)
from .pipes import MarkElementWidget, Pipe, Pipeline
from .tools import Tool


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@jupyrdf/jupyter-elk"}]


__all__ = [
    "__version__",
    "Diagram",
    "ElementLoader",
    "ElkJSONLoader",
    "from_element",
    "from_elkjson",
    "from_nx",
    "Loader",
    "MarkElementWidget",
    "NXLoader",
    "Pipe",
    "Pipeline",
    "Tool",
    "Viewer",
]
