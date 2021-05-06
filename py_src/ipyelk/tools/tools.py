# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


import ipywidgets as W
import traitlets as T

from ..diagram import Diagram


class ToolButton(W.Button):
    diagram: Diagram = T.Instance(Diagram)

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
        self.diagram.view.fit()
