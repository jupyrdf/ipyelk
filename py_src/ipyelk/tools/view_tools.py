# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from .tool import Tool


class Selection(Tool):
    ids = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids currently selected

    def to_element(self):
        map(self.source.from_id, self.selected)


class Hover(Tool):
    ids: str = T.Unicode().tag(sync=True)  # list element ids currently hovered


class Pan(Tool):
    origin = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)
    bounds = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)


class Zoom(Tool):
    zoom = T.Float(allow_none=True).tag(sync=True)


class Painter(Tool):
    cssClasses = T.Unicode(default_value="")
    marks = T.List()  # list of ids?
    name = T.Unicode()


class ToggleCollapsedTool(Tool):
    selection = T.Instance(Selection)

    def handler(self, *args):
        value: Node = self.tee.inlet.value
        should_refresh = False
        for selected in self.app.selected:
            for node in self.get_related(selected):
                self.toggle(node)
                should_refresh = True

        # trigger refresh if needed
        if should_refresh:
            self.app.refresh()

    def get_related(self, node):
        value: Node = self.tee.inlet.value
        tree = self.app.transformer.source[1]
        if tree and node in tree:
            return tree.neighbors(node)
        return []
