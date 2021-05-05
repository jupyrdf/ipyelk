# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    BaseElement,
    ElementIndex,
    HierarchicalElement,
    Node,
    Registry,
    elk_serialization,
)


class MarkIndex(W.DOMWidget):
    elements: ElementIndex = T.Instance(ElementIndex, allow_none=True)
    context: Registry = T.Instance(Registry, kw={})

    def update(self, *elements):
        self.elements = ElementIndex.from_els(*elements)
        return self

    def to_id(self, element: BaseElement):
        return element.get_id()

    def from_id(self, key) -> HierarchicalElement:
        return self.elements.get(key)


class MarkElementWidget(W.DOMWidget):
    value = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)
    index = T.Instance(MarkIndex)
    flow = TypedTuple(T.Unicode(), kw={})

    @T.default("index")
    def _default_index(self):
        return MarkIndex().update(self.value)
