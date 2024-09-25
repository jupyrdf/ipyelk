# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from .constants import EXTENSION_NAME, __version__
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
    from .js import __prefix__

    return [dict(src=str(__prefix__), dest=EXTENSION_NAME)]


__all__ = [
    "__version__",
    "_jupyter_labextension_paths",
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
