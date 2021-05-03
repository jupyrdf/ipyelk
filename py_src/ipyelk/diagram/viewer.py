# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import MarkElementWidget
from ..tools import Hover, Painter, Pan, Selection, Zoom


class Viewer(W.Widget):
    source: MarkElementWidget = T.Instance(MarkElementWidget, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )

    selection: Selection = T.Instance(Selection, kw={}).tag(
        sync=True, **W.widget_serialization
    )
    hover: Hover = T.Instance(Hover, kw={}).tag(sync=True, **W.widget_serialization)
    painter: Painter = T.Instance(Painter, kw={}).tag(
        sync=True, **W.widget_serialization
    )
    zoom = T.Instance(Zoom, kw={}).tag(sync=True, **W.widget_serialization)
    pan = T.Instance(Pan, kw={}).tag(sync=True, **W.widget_serialization)

    viewed: Tuple[str] = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids in the current view bounding box

    def fit(self):
        pass

    def center(self):
        pass
