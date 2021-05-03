# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T

from ipywidgets.widgets.trait_types import TypedTuple
from typing import Iterator

from ..elements import ElementIndex, BaseElement
from ..pipes import Pipe
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


class Painter(Tool):
    cssClasses = T.Unicode(default_value="")
    marks = T.List()  # list of ids?
    name = T.Unicode()
