"""Widget for interacting with ELK rendered using Sprotty
"""
import enum
import traitlets as T

from ipywidgets import DOMWidget, CallbackDispatcher
from traitlets import HasTraits, UseEnum
from typing import List

from .._version import EXTENSION_SPEC_VERSION
module_name = "elk-widget"



class Interactions(enum.Enum):
    select = 1         # -- IMPLICIT: default_value
    toggle = 2


class ElkDiagram(DOMWidget):
    """Jupyterlab widget for interacting with ELK diagrams
    """

    _model_name = T.Unicode("ELKModel").tag(sync=True)
    _model_module = T.Unicode(module_name).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKView").tag(sync=True)
    _view_module = T.Unicode(module_name).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    value = T.Dict().tag(sync=True)
    _mark_layout = T.Dict().tag(sync=True)
    selected = T.Tuple().tag(sync=True)
    hovered = T.Unicode(allow_none=True, default_value=None).tag(sync=True)
    # interaction = T.UseEnum(Interactions).tag(sync=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._click_handlers = CallbackDispatcher()
        self.on_msg(self._handle_click_msg)

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

    def center(self, model_ids: List[str] = None):
        """Center Diagram View on specified model ids
        
        :param model_ids: [description], defaults to None
        :type model_ids: List[str], optional
        """
        self.send({"action": "center", "model_id": model_ids})

