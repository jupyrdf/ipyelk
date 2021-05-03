# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ..elements import (
    Registry,
    VisIndex,
    exclude_hidden,
    exclude_layout,
    from_elkjson,
    index,
    Node,
    BaseElement,
    ElementIndex,
)
from .base import Pipe

import traitlets as T

# from ..elements import Node
from ..tools import Tool, Selection
# from .view_tools import Selection


class ToggleCollapsedTool(Tool):
    selection:Selection = T.Instance(Selection)

    def handler(self, *args):
        should_refresh = False
        index = self.tee.inlet.get_index()
        for selected in map(index.get, self.selection.ids):
            for element in self.get_related(selected):
                self.toggle(element)
                should_refresh = True

        # trigger refresh if needed
        if should_refresh:
            self.tee.dirty = True

    def get_related(self, element:BaseElement):
        print("get_related", element.id)
        if isinstance(element, Node):
            return element.children

        return []

    def toggle(self, element: BaseElement):
        """Toggle the `hidden` state for the given Node"""
        print('vis', id(element), element.id, not element.properties.hidden)
        element.properties.hidden = not element.properties.hidden


class VisibilityPipe(Pipe):
    collapser = T.Instance(ToggleCollapsedTool)

    @T.default("collapser")
    def _default_collapser(self):
        return ToggleCollapsedTool(tee=self)

    async def run(self):
        if self.outlet is None or self.inlet is None:
            return

        root = self.inlet.value
        # generate an index of hidden elements
        vis_index = VisIndex.from_els(root)
        print("hidden  #", len(vis_index))

        # TODO check if a change occurred
        if len(vis_index):
            # serialize the elements excluding hidden
            with exclude_hidden, exclude_layout:
                data = root.dict()

            # new root node with slack edges / ports introduced due to hidden
            # elements
            with Registry():
                value = from_elkjson(data, vis_index)

                for el in index.iter_elements(value):
                    el.id = el.get_id()
            self.outlet.value = value
        else:
            self.outlet.value = self.inlet.value

        return self.outlet
