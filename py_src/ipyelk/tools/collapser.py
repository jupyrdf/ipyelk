# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import traitlets as T

from ..elements import BaseElement, Node
from ..pipes import flows as F

# from ..elements import Node
from .tool import Tool
from .view_tools import Selection


class ToggleCollapsedTool(Tool):
    selection: Selection = T.Instance(Selection)

    @T.default("reports")
    def _default_reports(self):
        return (F.Node.hidden,)

    async def run(self):
        should_refresh = False
        index = self.tee.inlet.index
        for selected in map(index.from_id, self.selection.ids):
            for element in self.get_related(selected):
                self.toggle(element)
                should_refresh = True

        # trigger refresh if needed
        if should_refresh:
            self.tee.inlet.flow = self.reports

    def get_related(self, element: BaseElement):
        if isinstance(element, Node):
            return element.children
        return []

    def toggle(self, element: BaseElement) -> bool:
        """Toggle the `hidden` state for the given Node"""
        hidden = not element.properties.hidden
        element.properties.hidden = hidden
        return hidden
