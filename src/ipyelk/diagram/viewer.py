# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import math
from collections.abc import Sequence

import ipywidgets as W
import traitlets as T

from ..exceptions import RemovedAPI, check_removed
from ..pipes import MarkElementWidget
from ..pipes.util import resync_stale
from ..tools import (
    CenterTool,
    ControlOverlay,
    FitTool,
    Hover,
    Painter,
    Selection,
    Viewport,
)
from ..util import close_own_layout, own_layout


class Viewer(W.Widget):
    """Generic Viewer of ELK JSON diagrams. Currently only mainly used by :py:class:`~ipyelk.diagram.SprottyViewer`

    Attributes
    ----------
    :parameter source: :py:class:`~ipyelk.pipes.MarkElementWidget`
        input source for rendering.
    :parameter selection: :py:class:`~ipyelk.tools.Selection`
        maintains selected ids and methods to resolve the python elements.
    :parameter hover: :py:class:`~ipyelk.tools.Hover`
        maintains the hovered id.
    :parameter viewport: :py:class:`~ipyelk.tools.Viewport`
        the camera (origin, zoom, canvas size, viewed ids) of the most recently
        reporting view, written by the browser. Move a view with
        :py:meth:`~ipyelk.diagram.SprottyViewer.set_viewport`.
    :parameter painter: :py:class:`~ipyelk.tools.Painter`
        temporary, view-only CSS classes per element id, applied in every view
        without touching the model.
    :parameter control_overlay: :py:class:`~ipyelk.tools.ControlOverlay` or ``None``
        additional JupyterLab widgets that can be rendered on top of the diagram
        based on the current selected states. Opt-in: ``None`` (the default) and
        an overlay without ``children`` render nothing.
    :parameter fit_on_first_layout: bool
        opt-in (default ``False``): each view fits the whole diagram, in the browser,
        after its first layout, so a diagram displayed after it was laid out (when a
        :py:meth:`fit` message would have reached no view) does not open at 1:1 in
        the top-left corner. A view that is hidden then (a collapsed accordion, a
        background tab) fits the first time it is shown. Each view fits once: later
        layouts (a new ``source`` included), reveals and resizes keep its camera, and
        a ``set_viewport`` sent while it waits to be shown cancels its fit; a
        :py:meth:`fit` or :py:meth:`center` sent then has no canvas to work on, and
        the first fit replaces it. Set it before a view's first layout: a view that
        was already laid out is not fitted when it is turned on.
    :parameter fit_padding: float
        padding around the diagram, in diagram units (scaled by the zoom on screen),
        for the first-layout fit and for :py:meth:`fit` calls that pass no
        ``padding`` (default ``0``).
    :parameter fit_max_zoom: float or ``None``
        zoom limit for the first-layout fit and for :py:meth:`fit` calls that pass no
        ``max_zoom``; ``None`` (the default) leaves only the viewer's own limit (10),
        so a small diagram fills the view. A value above 10 acts as 10.
    :parameter cull_offscreen: bool
        default ``True``: each view renders only the elements that touch its canvas,
        which keeps selection, hover and panning cheap on a large diagram that is
        zoomed in; a diagram that fits on screen is drawn whole. The SVG in the page
        is then not the whole diagram. An :py:class:`~ipyelk.diagram.Exporter` renders
        its export from the model, so it is complete at any zoom; code that reads the
        browser DOM and needs every element there should set this to ``False``.

    """

    source = T.Instance(MarkElementWidget, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )

    selection = T.Instance(Selection, kw={}).tag(sync=True, **W.widget_serialization)
    hover = T.Instance(Hover, kw={}).tag(sync=True, **W.widget_serialization)
    viewport = T.Instance(Viewport, kw={}).tag(sync=True, **W.widget_serialization)
    painter = T.Instance(Painter, kw={}).tag(sync=True, **W.widget_serialization)
    control_overlay = T.Instance(
        ControlOverlay, allow_none=True, default_value=None
    ).tag(sync=True, **W.widget_serialization)

    fit_on_first_layout = T.Bool(False).tag(sync=True)
    fit_padding = T.Float(0.0, min=0.0).tag(sync=True)
    fit_max_zoom = T.Float(None, allow_none=True).tag(sync=True)
    cull_offscreen = T.Bool(True).tag(sync=True)

    fit_tool = T.Instance(FitTool)
    center_tool = T.Instance(CenterTool)

    #: removed names raise :class:`~ipyelk.exceptions.DeprecatedAPIError` through 3.x
    zoom = RemovedAPI(
        "Viewer.zoom was removed in ipyelk 3.0: the Zoom tool was a placeholder that "
        "nothing ever wrote. Read viewer.viewport.zoom (the browser's latest report, "
        "None until one arrives) and move a view with viewer.set_viewport(zoom=...). "
        "No alias: this error is raised throughout 3.x."
    )
    pan = RemovedAPI(
        "Viewer.pan was removed in ipyelk 3.0: the Pan tool was a placeholder that "
        "nothing ever wrote. Read viewer.viewport.origin and viewer.viewport.canvas_size "
        "(the browser's latest report, None until one arrives) and move a view with "
        "viewer.set_viewport(origin=(x, y)). No alias: this error is raised throughout "
        "3.x."
    )
    viewed = RemovedAPI(
        "Viewer.viewed was removed in ipyelk 3.0: nothing ever wrote it. Read "
        "viewer.viewport.viewed_ids (the ids whose bounds touch the reporting view's "
        "visible rectangle; None until the browser reports). No alias: this error is "
        "raised throughout 3.x."
    )

    def __init__(self, *args, **kwargs):
        check_removed(type(self), kwargs)
        self._stale_resync_at: float = 0.0
        self._stale_resync_interval: float = 0.0
        super().__init__(*args, **kwargs)
        self._own_layout = own_layout(self, kwargs)
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

    def close(self):
        """Close the viewer and its tools, not ``source`` or ``control_overlay``."""
        for name in (
            "selection",
            "hover",
            "viewport",
            "painter",
            "fit_tool",
            "center_tool",
        ):
            tool = self._trait_values.get(name)
            if tool is not None:
                tool.close()
        super().close()
        close_own_layout(self)

    @T.observe("source")
    def _reset_stale_throttle(self, change: T.Bunch | None = None):
        self._stale_resync_interval = 0.0

    @T.observe("source")
    def _sync_source_value(self, change: T.Bunch) -> None:
        if change.new is not None:
            change.new.sync_value()  # the browser draws ``source.value``

    @T.validate("fit_padding", "fit_max_zoom")
    def _validate_fit_defaults(self, proposal: T.Bunch) -> float | None:
        """Refuse values JSON cannot carry or a fit cannot use (NaN, inf, zoom <= 0)."""
        name, value = proposal["trait"].name, proposal["value"]
        if value is None:
            return value
        if not math.isfinite(value) or (name == "fit_max_zoom" and value <= 0):
            kind = "a finite padding >= 0" if name == "fit_padding" else "a zoom > 0"
            msg = f"{name} must be {kind}, not {value!r}"
            raise T.TraitError(msg)
        return value

    @T.default("fit_tool")
    def _default_fit_tool(self) -> FitTool:
        return FitTool(on_click=lambda *_: self.fit())

    @T.default("center_tool")
    def _default_center_tool(self) -> CenterTool:
        return CenterTool(on_click=lambda *_: self.center())

    def fit(
        self,
        model_ids: str | Sequence[str] | None = None,
        animate: bool | None = None,
        max_zoom: float | None = None,
        padding: float | None = None,
    ) -> None:
        """Pan/zoom the view to focus on ``model_ids`` (the whole diagram if None).

        A ``str`` is one id, never a sequence of characters. The generic viewer has
        no viewport of its own, so this does nothing; subclasses that render
        (:py:class:`~ipyelk.diagram.SprottyViewer`) implement it with the same
        signature.
        """

    def center(
        self,
        model_ids: str | Sequence[str] | None = None,
        animate: bool | None = None,
        retain_zoom: bool | None = None,
    ) -> None:
        """Center the view on ``model_ids`` (the whole diagram if None).

        A ``str`` is one id, never a sequence of characters. The generic viewer has
        no viewport of its own, so this does nothing; subclasses that render
        (:py:class:`~ipyelk.diagram.SprottyViewer`) implement it with the same
        signature.
        """
