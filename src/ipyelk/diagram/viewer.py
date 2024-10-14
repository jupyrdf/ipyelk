# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import MarkElementWidget
from ..tools import CenterTool, ControlOverlay, FitTool, Hover, Pan, Selection, Zoom


class Viewer(W.Widget):
    """Generic Viewer of ELK Json diagrams. Currently only mainly used by :py:class:`~ipyelk.diagram.SprottyViewer`

    Attributes
    ----------
    source: :py:class:`~ipyelk.pipes.MarkElementWidget`
        input source for rendering.
    selection: :py:class:`~ipyelk.tools.Selection`
        maintains selected ids and methods to resolve the python elements.
    hover: :py:class:`~ipyelk.tools.Hover`
        maintains hovered ids.
    zoom: :py:class:`~ipyelk.tools.Zoom`

    pan: :py:class:`~ipyelk.tools.Pan`

    control_overlay: :py:class:`~ipyelk.tools.ControlOverlay`
        additional jupyterlab widgets that can be rendered ontop of the diagram
        based on the current selected states.

    """

    source: MarkElementWidget = T.Instance(MarkElementWidget, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )

    selection: Selection = T.Instance(Selection, kw={}).tag(
        sync=True, **W.widget_serialization
    )
    hover: Hover = T.Instance(Hover, kw={}).tag(sync=True, **W.widget_serialization)
    zoom = T.Instance(Zoom, kw={}).tag(sync=True, **W.widget_serialization)
    pan = T.Instance(Pan, kw={}).tag(sync=True, **W.widget_serialization)
    control_overlay: ControlOverlay = T.Instance(ControlOverlay, kw={}).tag(
        sync=True, **W.widget_serialization
    )

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
