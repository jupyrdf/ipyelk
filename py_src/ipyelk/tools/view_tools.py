# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Iterator

import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import BaseElement
from ..pipes import MarkIndex
from .tool import Tool, ToolButton


class Selection(Tool):
    ids = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids currently selected

    def get_index(self) -> MarkIndex:
        if self.tee is None:
            raise ValueError("Tool not attached to a pipe")
        if self.tee.inlet.index is None:
            # make the element index
            self.tee.inlet.build_index()
        return self.tee.inlet.index

    def elements(self) -> Iterator[BaseElement]:
        index = self.get_index()
        for el in map(index.from_id, self.ids):
            yield el


class Hover(Tool):
    ids: str = T.Unicode().tag(sync=True)  # list element ids currently hovered


class Pan(Tool):
    origin = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)
    bounds = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)


class Zoom(Tool):
    zoom = T.Float(allow_none=True).tag(sync=True)


class FitTool(ToolButton):
    description: str = T.Unicode(default_value="Fit")


class CenterTool(ToolButton):
    description: str = T.Unicode(default_value="Center")
