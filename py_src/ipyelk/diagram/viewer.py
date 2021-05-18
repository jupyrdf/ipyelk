# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import MarkElementWidget
from ..tools import CenterTool, FitTool, Hover, Pan, Selection, Zoom


class Viewer(W.Widget):
    source: MarkElementWidget = T.Instance(MarkElementWidget, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )

    selection: Selection = T.Instance(Selection, kw={}).tag(
        sync=True, **W.widget_serialization
    )
    hover: Hover = T.Instance(Hover, kw={}).tag(sync=True, **W.widget_serialization)
    zoom = T.Instance(Zoom, kw={}).tag(sync=True, **W.widget_serialization)
    pan = T.Instance(Pan, kw={}).tag(sync=True, **W.widget_serialization)

    viewed: Tuple[str] = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids in the current view bounding box
    fit_tool: FitTool = T.Instance(FitTool)
    center_tool: CenterTool = T.Instance(CenterTool)

    @T.default("fit_tool")
    def _default_fit_tool(self) -> FitTool:
        return FitTool(handler=lambda _: self.fit())

    @T.default("center_tool")
    def _default_center_tool(self) -> CenterTool:
        return CenterTool(handler=lambda _: self.center())

    def fit(self):
        pass

    def center(self):
        pass
