"""Widget for interacting with ELK rendered using Sprotty
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import List

import traitlets as T
from ipywidgets import DOMWidget

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..elements import SymbolSpec, symbol_serialization
from ..tools import CenterTool, FitTool
from .viewer import Viewer

# TODO reconnect schema check after adding edge type
# from ..schema import ElkSchemaValidator
# from ..trait_types import Schema


class SprottyViewer(DOMWidget, Viewer):
    """Jupyterlab widget for displaying and interacting with views generated
    from elk json.

    Setting the instance's `value` traitlet to valid `elk json
    <https://www.eclipse.org/elk/documentation/tooldevelopers/
    graphdatastructure/jsonformat.html>`_  will call the `elkjs layout method
    <https://github.com/kieler/elkjs>`_ and display the returned `mark_layout`
    using `sprotty <https://github.com/eclipse/sprotty>`_.

    :param mark_layout: Input elk json layout
    :type mark_layout: Dict
    :param selected: elk ids of selected marks
    :type selected: Tuple[str]
    :param hovered: elk id of currently hovered mark
    :type hovered: str
    :param symbols: Symbol mapping to use for rendering
    :type symbols: SymbolSpec

    """

    _model_name = T.Unicode("ELKViewerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKViewerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    symbols: SymbolSpec = T.Instance(SymbolSpec, kw={}).tag(
        sync=True, **symbol_serialization
    )

    def center(
        self,
        model_ids: List[str] = None,
        animate: bool = None,
        retain_zoom: bool = None,
    ):
        """Center Diagram View on specified model ids

        :param model_ids: list of elk model id strings, defaults to None
        :param animate: specify is the view animates to the given marks
        :param retain_zoom: specify if the current zoom level is maintained
        """
        self.send(
            {
                "action": "center",
                "model_id": model_ids,
                "animate": True if animate is None else animate,
                "retain_zoom": False if retain_zoom is None else retain_zoom,
            }
        )

    def fit(
        self,
        model_ids: List[str] = None,
        animate: bool = None,
        max_zoom: float = None,
        padding: float = None,
    ):
        """Pan/Zoom the Diagram View to focus on particular model ids

        :param model_ids: list of elk model id strings, defaults to None
        :param animate: specify is the view animates to the given marks
        :param max_zoom: specify if the max zoom level
        :param padding: specify if the viewport padding around the marks
        """
        self.send(
            {
                "action": "fit",
                "model_id": model_ids,
                "animate": True if animate is None else animate,
                "max_zoom": max_zoom,
                "padding": padding,
            }
        )

    @T.default("fit_tool")
    def _default_fit_tool(self) -> FitTool:
        return FitTool(handler=lambda *_: self.fit(model_ids=self.selection.ids))

    @T.default("center_tool")
    def _default_center_tool(self) -> CenterTool:
        return CenterTool(handler=lambda *_: self.center(model_ids=self.selection.ids))
