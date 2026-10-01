# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Widget for interacting with ELK rendered using Sprotty"""

from __future__ import annotations

from collections.abc import Sequence

import traitlets as T
from ipywidgets import DOMWidget

from ..constants import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..elements import SymbolSpec, symbol_serialization
from ..tools import CenterTool, FitTool
from .viewer import Viewer

# TODO reconnect schema check after adding edge type
# from ..schema import ElkSchemaValidator
# from ..trait_types import Schema


class SprottyViewer(DOMWidget, Viewer):
    """Jupyterlab widget for displaying and interacting with views generated
    from ELK JSON.

    Setting the instance's `value` traitlet to valid `Eclipse Layout Kernel JSON
    <https://www.eclipse.org/elk/documentation/tooldevelopers/
    graphdatastructure/jsonformat.html>`_  will call the `elkjs layout method
    <https://github.com/kieler/elkjs>`_ and display the returned `mark_layout`
    using `sprotty <https://github.com/eclipse/sprotty>`_.

    """

    _model_name = T.Unicode("ELKViewerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKViewerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    symbols = T.Instance(SymbolSpec, kw={}).tag(sync=True, **symbol_serialization)

    def center(
        self,
        model_ids: str | Sequence[str] | None = None,
        animate: bool | None = None,
        retain_zoom: bool | None = None,
    ) -> None:
        """Center Diagram View on specified model ids

        :param model_ids: one elk model id, or a sequence of them; None (default)
            centers the whole diagram
        :param animate: specify is the view animates to the given marks
        :param retain_zoom: specify if the current zoom level is maintained
        """
        self.send({
            "action": "center",
            "model_id": _id_list(model_ids),
            "animate": True if animate is None else animate,
            "retain_zoom": False if retain_zoom is None else retain_zoom,
        })

    def fit(
        self,
        model_ids: str | Sequence[str] | None = None,
        animate: bool | None = None,
        max_zoom: float | None = None,
        padding: float | None = None,
    ) -> None:
        """Pan/Zoom the Diagram View to focus on particular model ids

        :param model_ids: one elk model id, or a sequence of them; None (default)
            fits the whole diagram
        :param animate: specify is the view animates to the given marks
        :param max_zoom: specify if the max zoom level
        :param padding: specify if the viewport padding around the marks
        """
        self.send({
            "action": "fit",
            "model_id": _id_list(model_ids),
            "animate": True if animate is None else animate,
            "max_zoom": max_zoom,
            "padding": padding,
        })

    def set_viewport(
        self,
        *,
        origin: tuple[float, float] | None = None,
        zoom: float | None = None,
        animate: bool = True,
        view_id: str | None = None,
    ) -> None:
        """Move the camera of the connected view(s).

        A command, not state: the browser applies it and then reports the resulting
        camera through :py:attr:`~ipyelk.diagram.Viewer.viewport`.

        :param origin: diagram coordinates for the canvas top-left corner; ``None``
            keeps the view's current origin
        :param zoom: CSS pixels per diagram unit; ``None`` keeps the current zoom
        :param animate: animate the move (default) or jump
        :param view_id: only the view with this id (see
            :py:attr:`ipyelk.tools.Viewport.view_id`); ``None`` moves every
            connected view
        """
        self.send({
            "action": "viewport",
            "origin": None if origin is None else [float(origin[0]), float(origin[1])],
            "zoom": None if zoom is None else float(zoom),
            "animate": animate,
            "view_id": view_id,
        })

    @T.default("fit_tool")
    def _default_fit_tool(self) -> FitTool:
        return FitTool(on_click=lambda *_: self.fit(model_ids=self.selection.ids))

    @T.default("center_tool")
    def _default_center_tool(self) -> CenterTool:
        return CenterTool(on_click=lambda *_: self.center(model_ids=self.selection.ids))


def _id_list(model_ids: str | Sequence[str] | None) -> list[str] | None:
    """Normalize the ``model_id`` payload: a ``str`` is one id, not its characters."""
    if model_ids is None:
        return None
    if isinstance(model_ids, str):
        return [model_ids]
    return list(model_ids)
