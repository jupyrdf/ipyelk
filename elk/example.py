#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Dane Freeman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget, CallbackDispatcher
from traitlets import Dict, Unicode, List, Tuple
from ._version import EXTENSION_SPEC_VERSION

module_name = "elk-widget"


class ELKWidget(DOMWidget):
    """TODO: Add docstring here
    """
    _model_name = Unicode('ELKModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = Unicode('ELKView').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    value = Dict().tag(sync=True)
    diagram = Dict().tag(sync=True)
    selected = Tuple().tag(sync=True)
    hovered = Unicode(allow_none=True, default_value=None).tag(sync=True)

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
        self.evt = dict(a=_,b=buffers,c=content)
        if content.get('event', '') == 'click':
            self.click(content.get('id',''))        