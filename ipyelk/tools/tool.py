import asyncio
import ipywidgets as W
import traitlets as T

from ipywidgets import CallbackDispatcher
from typing import Callable

from ..styled_widget import StyledWidget


class Toolbar(W.HBox, StyledWidget):
    """Toolbar for ScienceScout Tools"""
    commands = T.List(T.Instance(W.Widget), kw={})
    close_btn = T.Instance(W.Button)
    def __init__(self, *args, **kwargs):
        super(). __init__(*args, **kwargs)
        self.add_class("toolbar")
        self._update_children()
        
    @T.default("close_btn")
    def _default_cls_btn(self):
        return W.Button(icon="times-circle").add_class("close-btn")

    @T.observe("commands")
    def _update_children(self, change:T.Bunch=None):
        self.children = self.commands + [self.close_btn]

    @T.default("style")
    def _default_style(self):
        return {
            " .close-btn": {
                "display":"block",
                "margin-left":"auto",
                "width": "var(--jp-widgets-inline-height)",
                "padding":"0",
                "background":"inherit",
                "border": "inherit",
                "outline":"inherit",
            },
            " .close-btn:hover": {
                "box-shadow":"inherit",
                "color":"var(--jp-warn-color0)",
            }
        }
        
class Tool(W.VBox, StyledWidget):
    toolbar: Toolbar = T.Instance(Toolbar)
    view: W.Widget = T.Instance(W.Widget,kw={})
    manager = T.Any()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toolbar.close_btn.on_click(self.on_close)
        self._change_view()

    @T.observe('view')
    def _change_view(self, change:T.Bunch=None):
        self.children = [W.VBox(children=[
            self.view,
            self.toolbar.add_class("toolbar")
        ]).add_class("tool-view")]

    @T.default("style")
    def _default_style(self):
        return {
            "":{
                'padding':0,
                
            },
            " .widget-button": {
                "width": "var(--jp-widgets-inline-height)",
                "padding": "0",
            },
            " .tool-view":{
                'flex': '1',
                'border-style': 'solid',
                'border-width': '1px',
                'padding': '5px',
                "overflow": "hidden",
            },
            " .toolbar": {
                "width": "100%",
                "visibility":"hidden",
                "position":"absolute",
                "opacity": "0",
                "transition": "all 0.2s ease",
                "transform": "translateY(calc(0px - var(--jp-widgets-inline-height)))",
            },
            " :hover .toolbar": {
                "visibility":"visible",
                "opacity": ".25",
                "transform":"translateY(0)",
            },
            " .toolbar:hover": {
                "opacity": "1",
            },
        }
    
    @T.default("toolbar")
    def _default_toolbar(self):
        tb = Toolbar()
        return tb

    def on_close(self, cb):
        if hasattr(self.manager, "remove"):
            self.manager.remove(self)

    def refresh(self):
        """Subclasses should implement"""
        pass