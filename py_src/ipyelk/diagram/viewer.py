# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import MarkElementWidget


class Tool(W.Widget):
    pass


class Highlighter(W.Widget):
    cssClasses = T.Unicode(default_value="")
    marks = T.List()  # list of ids?
    name = T.Unicode()


class Viewer(W.Widget):
    tools: Tuple[Tool] = T.List(T.Instance(Tool)).tag(
        sync=True, **W.widget_serialization
    )
    source: MarkElementWidget = T.Instance(MarkElementWidget, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )

    selected: Tuple[str] = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids currently selected
    hovered: str = T.Unicode().tag(sync=True)  # list element ids currently hovered

    highlighters: Tuple[Highlighter] = TypedTuple(trait=T.Instance(Highlighter)).tag(
        sync=True, **W.widget_serialization
    )
    viewed: Tuple[str] = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids in the current view bounding box

    zoom = T.Float(allow_none=True).tag(sync=True)
    origin = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)
    bounds = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)

    def fit(self):
        pass

    def center(self):
        pass

    def to_element(self):
        map(self.source.from_id, self.selected)
