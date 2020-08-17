# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


import ipywidgets as W
import traitlets as T

from ..app import Elk, ElkDiagram
from ..nx import XELK


class ToolButton(W.Button):
    app: Elk = T.Instance(Elk)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_click(self.handler)

    def handler(self, *args):
        raise NotImplementedError("Subclasses should implement the tool handler")


class ToggleCollapsedBtn(ToolButton):
    @T.default("description")
    def _default_description(self):
        return "Toggle Collapsed"

    def handler(self, *args):
        diagram: ElkDiagram = self.app.diagram
        transformer: XELK = self.app.transformer
        graph, tree = transformer.source
        for element_id in diagram.selected:
            if element_id in tree:
                for child in tree.neighbors(element_id):
                    state = tree.nodes[child].get("hidden", False)
                    tree.nodes[child]["hidden"] = not state
                self.app.refresh()
