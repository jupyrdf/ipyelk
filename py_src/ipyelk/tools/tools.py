# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


import ipywidgets as W
import traitlets as T

from ...elements import Node
from ..app import Elk, ElkDiagram


class ToolButton(W.Button):
    app: Elk = T.Instance(Elk)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_click(self.handler)

    def handler(self, *args):
        raise NotImplementedError("Subclasses should implement the tool handler")



class FitBtn(ToolButton):
    @T.default("description")
    def _default_description(self):
        return "Fit"

    def handler(self, *args):
        diagram: ElkDiagram = self.app.diagram
        diagram.fit()
