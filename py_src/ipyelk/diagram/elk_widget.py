"""Widget for interacting with ELK rendered using Sprotty
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import List

import traitlets as T
from ipywidgets import CallbackDispatcher, DOMWidget, widget_serialization

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..layouting.elkjs import ElkJS
from ..schema import ElkSchemaValidator
from ..trait_types import Schema
from .symbol.defs import Def, def_serialization


class ElkDiagram(DOMWidget):
    """Jupyterlab widget for interacting with ELK diagrams"""

    _model_name = T.Unicode("ELKDiagramModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKDiagramView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    value = Schema(ElkSchemaValidator).tag(sync=True)
    defs = T.Dict(value_trait=T.Instance(Def), kw={}).tag(
        sync=True, **def_serialization
    )
    mark_layout = T.Dict().tag(sync=True)
    selected = T.Tuple().tag(sync=True)
    hovered = T.Unicode(allow_none=True, default_value=None).tag(sync=True)
    layouter = T.Instance(ElkJS, kw={}).tag(sync=True, **widget_serialization)

    def __init__(self, *value, **kwargs):
        if value:
            kwargs["value"] = value[0]
        defs = kwargs.pop("defs", {})
        super().__init__(**kwargs)
        self._click_handlers = CallbackDispatcher()
        self.on_msg(self._handle_click_msg)
        # defs are using the model_id to serialize so need the rest of the
        # widget to initialize before setting the `defs` trait
        self.defs = defs

    @T.default("value")
    def _default_value(self):
        return {"id": "root"}

    def on_click(self, callback, remove=False):
        """Register a callback to execute when the button is clicked.
        The callback will be called with one argument, the clicked button
        widget instance.
        Parameters
        ----------
        remove: bool (optional)
            Set to true to remove the callback from the list of callbacks.
        """
        self._click_handlers.register_callback(callback, remove=remove)

    def click(self, element_id):
        """Programmatically trigger a click event.
        This will call the callbacks registered to the clicked button
        widget instance.
        """
        self._click_handlers(self, element_id)

    def _handle_click_msg(self, _, content, buffers):
        """Handle a msg from the front-end.
        Parameters
        ----------
        content: dict
            Content of the msg.
        """
        if content.get("event", "") == "click":
            self.click(content.get("id", ""))

    def center(
        self,
        model_ids: List[str] = None,
        animate: bool = None,
        retain_zoom: bool = None,
    ):
        """Center Diagram View on specified model ids

        :param model_ids: [description], defaults to None
        :type model_ids: List[str], optional
        :type animate: bool, optional
        :type retain_zoom: bool, optional
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
        """Pan/Zoom the Diagram View to focus on particular model ids"""
        self.send(
            {
                "action": "fit",
                "model_id": model_ids,
                "animate": True if animate is None else animate,
                "max_zoom": max_zoom,
                "padding": padding,
            }
        )
