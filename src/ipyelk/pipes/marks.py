# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    BaseElement,
    ElementIndex,
    Node,
    Registry,
    elk_serialization,
)


class MarkIndex(W.DOMWidget):
    elements = T.Instance(ElementIndex, allow_none=True)
    context = T.Instance(Registry, kw={})

    _root: Node | None = None

    def to_id(self, element: BaseElement):
        return element.get_id()

    def from_id(self, key: str) -> BaseElement:
        elements = self.elements
        if elements is None:
            raise ValueError("Can't have no elements!")
        element = elements.get(key)
        return element

    @property
    def root(self) -> Node:
        if self._root is None:
            self._update_root()
        if self._root is None:
            raise ValueError("Root cannot be None after updating it!")
        return self._root

    @T.observe("elements")
    def _update_root(self, change: T.Bunch | None = None):
        self._root = None
        if self.elements:
            self._root = self.elements.root()


class MarkElementWidget(W.DOMWidget):
    value = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)
    index = T.Instance(MarkIndex, kw={}).tag(sync=True, **W.widget_serialization)
    flow: tuple[str, ...] = TypedTuple(T.Unicode(), kw={}).tag(sync=True)

    def persist(self, rebuild_index: bool = False):
        """Fold ``value`` into the shared index.

        The index -- not ``value`` -- is the authority for the element
        hierarchy: hidden elements never survive serialization (see
        ``Node.model_dump``), so the index must be merged into, never rebuilt from, a
        value that has been through the browser.  ``rebuild_index`` is kept for
        the initial build only.
        """
        if rebuild_index or self.index.elements is None:
            self.build_index()
        elif self.value is not None:
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

    def _repr_mimebundle_(self, **kwargs):
        from IPython.display import JSON, display

        if self.value:
            display(JSON(self.value.model_dump()))
