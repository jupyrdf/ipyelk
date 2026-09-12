# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from ..exceptions import DeprecatedAPIError
from .collapser import ToggleCollapsedTool
from .control_overlay import ControlOverlay
from .painter import Painter
from .progress import PipelineProgressBar
from .tool import Tool, ToolButton
from .toolbar import Toolbar
from .view_tools import CenterTool, FitTool, Hover, Selection, SetTool, Viewport

# a module ``__getattr__`` can only live in the package module itself
#: removed class names raise :class:`~ipyelk.exceptions.DeprecatedAPIError` through 3.x
_REMOVED = {  # ruff: ignore[non-empty-init-module]
    "Zoom": (
        "ipyelk.tools.Zoom was removed in ipyelk 3.0: it was a placeholder that "
        "nothing ever wrote. The browser reports the camera of the most recently "
        "reporting view as viewer.viewport (ipyelk.tools.Viewport: view_id, origin, "
        "zoom, canvas_size, viewed_ids); move a view with viewer.set_viewport(zoom=...). "
        "No alias: this error is raised throughout 3.x."
    ),
    "Pan": (
        "ipyelk.tools.Pan was removed in ipyelk 3.0: it was a placeholder that "
        "nothing ever wrote. The browser reports the camera of the most recently "
        "reporting view as viewer.viewport (ipyelk.tools.Viewport: view_id, origin, "
        "zoom, canvas_size, viewed_ids); move a view with "
        "viewer.set_viewport(origin=(x, y)). No alias: this error is raised throughout "
        "3.x."
    ),
}


def __getattr__(name: str) -> object:
    if name in _REMOVED:
        raise DeprecatedAPIError(_REMOVED[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CenterTool",
    "ControlOverlay",
    "FitTool",
    "Hover",
    "Painter",
    "PipelineProgressBar",
    "Selection",
    "SetTool",
    "ToggleCollapsedTool",
    "Tool",
    "ToolButton",
    "Toolbar",
    "Viewport",
]
