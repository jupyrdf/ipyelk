# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Tuple

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

    _root: Node = None

    def to_id(self, element: BaseElement):
        return element.get_id()

    def from_id(self, key) -> HierarchicalElement:
        return self.elements.get(key)

    @property
    def root(self) -> Node:
        if self._root is None:
            self._update_root()
        return self._root

    @T.observe("elements")
    def _update_root(self, change=None):
        self._root = None
        if self.elements:
            self._root = self.elements.root()


class MarkElementWidget(W.DOMWidget):
    value: Node = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)
    index: MarkIndex = T.Instance(MarkIndex, kw={}).tag(
        sync=True, **W.widget_serialization
    )
    flow: Tuple[str] = TypedTuple(T.Unicode(), kw={}).tag(sync=True)

    def persist(self):
        if self.index.elements is None:
            self.build_index()
        else:
            self.index.elements.update(ElementIndex.from_els(self.value))
        return self

    def build_index(self) -> MarkIndex:
        if self.value is None:
            index = ElementIndex()
        else:
            with self.index.context:
                index = ElementIndex.from_els(self.value)
        self.index.elements = index
        return self.index
