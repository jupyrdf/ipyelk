# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W
import traitlets as T

from ..elements import BaseElement, Compartment, Node
from ..pipes import flows as F

# from ..elements import Node
from .tool import Tool
from .view_tools import Selection


class ToggleCollapsedTool(Tool):
    """Toggle the ``hidden`` state of the selected nodes' children.

    Needs a :py:class:`~ipyelk.tools.Selection`: until ``selection`` is bound the
    button is disabled and :meth:`~ipyelk.tools.Tool.trigger` raises.
    """

    selection = T.Instance(Selection, allow_none=True, default_value=None)
    _dependencies = ("selection",)

    @T.default("reports")
    def _default_reports(self):
        return (F.Node.hidden,)

    @T.default("ui")
    def _default_ui(self) -> W.DOMWidget:
        btn = W.Button(description="Toggle Collapsed")
        btn.on_click(self.trigger)
        return btn

    async def run(self):
        if self.selection is None:  # trigger() rejects this; run() called directly
            raise RuntimeError("ToggleCollapsedTool is not bound: selection is None")
        for selected in self.selection.elements():
            for element in self.get_related(selected):
                self.toggle(element)
        # the pending flow is recorded by the base class (``Tool.record_reports``)

    def get_related(self, element: BaseElement):
        if isinstance(element, Compartment):
            parent = element.get_parent()
            if parent:
                return parent.children[1:]
        if isinstance(element, Node):
            return element.children

        return []

    def toggle(self, element: BaseElement) -> bool:
        """Toggle the `hidden` state for the given Node"""
        hidden = not element.properties.hidden
        element.properties.hidden = hidden
        return hidden
