# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from .tool import Tool


class Selection(Tool):
    ids = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids currently selected


class Hover(Tool):
    ids: str = T.Unicode().tag(sync=True)  # list element ids currently hovered


class Pan(Tool):
    origin = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)
    bounds = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)


class Zoom(Tool):
    zoom = T.Float(allow_none=True).tag(sync=True)
