# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from collections import defaultdict
from itertools import chain
from typing import Dict, List

import ipywidgets as W
import traitlets as T

from ..styled_widget import StyledWidget
from .tool import Tool


class Toolbar(W.HBox, StyledWidget):
    """Toolbar for an Elk App"""

    tools = T.List(T.Instance(Tool), kw={})
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

    @T.observe("tools")
    def _update_children(self, change: T.Bunch = None):
        self.children = self.tool_order() + [self.close_btn]

        # only have widgets shown if commands are specified or a on_close callback
        shown = "visible" if self.tools or callable(self.on_close) else "hidden"
        self.layout.visibility = shown

    def tool_order(self) -> List[Tool]:
        return list(chain(*[values for k, values in sorted(self.order().items())]))

    def order(self) -> Dict[int, List[Tool]]:
        order = defaultdict(list)
        for tool in self.tools:
            if isinstance(tool.ui, W.DOMWidget):
                order[tool.priority].append(tool.ui)
        return order
