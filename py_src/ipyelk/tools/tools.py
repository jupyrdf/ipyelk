# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


import ipywidgets as W
import traitlets as T

from ..app import Elk, ElkDiagram


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

    def toggle(self, node):
        """Toggle the `hidden` state for the given networkx node"""
        tree = self.app.transformer.source[1]
        state = tree.nodes[node].get("hidden", False)
        tree.nodes[node]["hidden"] = not state

    def handler(self, *args):
        should_refresh = False
        for selected in self.app.selected:
            for node in self.get_related(selected):
                self.toggle(node)
                should_refresh = True

        # trigger refresh if needed
        if should_refresh:
            self.app.refresh()

    def get_related(self, node):
        tree = self.app.transformer.source[1]
        if tree and node in tree:
            return tree.neighbors(node)
        return []


class FitBtn(ToolButton):
    @T.default("description")
    def _default_description(self):
        return "Fit"

    def handler(self, *args):
        diagram: ElkDiagram = self.app.diagram
        diagram.fit()
