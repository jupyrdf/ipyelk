# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import MarkElementWidget
from ..pipes.util import resync_stale
from ..tools import CenterTool, ControlOverlay, FitTool, Hover, Pan, Selection, Zoom


class Viewer(W.Widget):
    """Generic Viewer of ELK Json diagrams. Currently only mainly used by :py:class:`~ipyelk.diagram.SprottyViewer`

    Attributes
    ----------
    :parameter source: :py:class:`~ipyelk.pipes.MarkElementWidget`
        input source for rendering.
    :parameter selection: :py:class:`~ipyelk.tools.Selection`
        maintains selected ids and methods to resolve the python elements.
    :parameter hover: :py:class:`~ipyelk.tools.Hover`
        maintains hovered ids.
    :parameter zoom: :py:class:`~ipyelk.tools.Zoom`
    :parameter pan: :py:class:`~ipyelk.tools.Pan`
    :parameter control_overlay: :py:class:`~ipyelk.tools.ControlOverlay`
        additional jupyterlab widgets that can be rendered on top of the diagram
        based on the current selected states.

    """

    source = T.Instance(MarkElementWidget, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )

    selection = T.Instance(Selection, kw={}).tag(sync=True, **W.widget_serialization)
    hover = T.Instance(Hover, kw={}).tag(sync=True, **W.widget_serialization)
    zoom = T.Instance(Zoom, kw={}).tag(sync=True, **W.widget_serialization)
    pan = T.Instance(Pan, kw={}).tag(sync=True, **W.widget_serialization)
    control_overlay = T.Instance(ControlOverlay, kw={}).tag(
        sync=True, **W.widget_serialization
    )

    viewed = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids in the current view bounding box
    fit_tool = T.Instance(FitTool)
    center_tool = T.Instance(CenterTool)

    def __init__(self, *args, **kwargs):
        self._stale_resync_at: float = 0.0
        self._stale_resync_interval: float = 0.0
        super().__init__(*args, **kwargs)
        self.on_msg(self._handle_browser_msg)

    def _handle_browser_msg(
        self, widget: W.Widget, content: dict[str, object], buffers: list[bytes] | None
    ):
        """Re-sync a frontend view that reports ``action: stale``.

        ``source`` starts ``None`` at comm-open and is rewired to the pipe
        outlet by a later state update -- one message a congested iopub
        channel may drop, leaving a blank diagram with no error. The frontend
        reports ``stale`` while it has nothing to render; re-emitting the
        viewer's state (and the source's, which carries the laid-out value)
        heals the divergence. See ``ipyelk.pipes.util.resync_stale``.
        """
        if isinstance(content, dict) and content.get("action") == "stale":
            resync_stale(self, self.source, missing=content.get("missing"))

    @T.observe("source")
    def _reset_stale_throttle(self, change: T.Bunch | None = None):
        self._stale_resync_interval = 0.0

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
