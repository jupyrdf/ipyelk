# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W
import traitlets as T

from .styled_widget import StyledWidget


class Toolbar(W.HBox, StyledWidget):
    """Toolbar for an Elk App"""

    commands = T.List(T.Instance(W.Widget), kw={})
    close_btn: W.Button = T.Instance(W.Button)
    on_close = T.Any(
        default_value=None
    )  # holds a callable function to execute when close button is pressed

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_class("jp-ElkToolbar")
        self._update_children()
        self._update_close_callback()

    @T.default("close_btn")
    def _default_cls_btn(self) -> W.Button:
        btn = W.Button(icon="times-circle").add_class("close-btn")

        def pressed(*args):
            if callable(self.on_close):
                self.on_close()

        btn.on_click(pressed)
        return btn

    @T.observe("on_close")
    def _update_close_callback(self, change: T.Bunch = None):
        """Toggle visiblity of the close button depending on if the `on_close` trait
        is callable
        """
        shown = "visible" if callable(self.on_close) else "hidden"
        self.close_btn.layout.visibility = shown

    @T.observe("commands")
    def _update_children(self, change: T.Bunch = None):
        self.children = self.commands + [self.close_btn]

        # only have widgets shown if commands are specified or a on_close callback
        shown = "visible" if self.commands or callable(self.on_close) else "hidden"
        self.layout.visibility = shown
