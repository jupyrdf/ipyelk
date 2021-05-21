# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Iterator, Set, Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import BaseElement
from ..pipes import MarkIndex
from .tool import Tool, ToolButton


class Selection(Tool):
    ids = TypedTuple(trait=T.Unicode()).tag(
        sync=True
    )  # list element ids currently selected

    def get_index(self) -> MarkIndex:
        if self.tee is None:
            raise ValueError("Tool not attached to a pipe")
        if self.tee.inlet.index is None:
            # make the element index
            self.tee.inlet.build_index()
        return self.tee.inlet.index

    def elements(self) -> Iterator[BaseElement]:
        index = self.get_index()
        for el in map(index.from_id, self.ids):
            yield el


class Hover(Tool):
    ids: str = T.Unicode().tag(sync=True)  # list element ids currently hovered


class Pan(Tool):
    origin = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)
    bounds = T.Tuple(T.Float(), T.Float(), allow_none=True).tag(sync=True)


class Zoom(Tool):
    zoom = T.Float(allow_none=True).tag(sync=True)


class FitTool(ToolButton):
    description: str = T.Unicode(default_value="Fit")


class CenterTool(ToolButton):
    description: str = T.Unicode(default_value="Center")


class SetTool(Tool):
    selection = T.Instance(Selection, allow_none=True)
    active = TypedTuple(T.Instance(BaseElement), kw={})
    css_classes = TypedTuple(T.Unicode())

    @T.default("css_classes")
    def _default_css_classes(self):
        return tuple(
            [
                "active-set",
            ]
        )

    @T.observe("active")
    def handler(self, change):

        try:
            new = set(change.new)
        except Exception:
            new = set()
        try:
            old = set(change.old)
        except Exception:
            old = set()

        exiting, entering = lifecycle(old, new)

        for el in entering:
            el.add_class(*self.css_classes)
        for el in exiting:
            el.remove_class(*self.css_classes)

    def add(self):
        self.active = tuple(set(self.active) | set(self.selection.elements()))

    def remove(self):
        self.active = tuple(set(self.active) - set(self.selection.elements()))

    def set_active(self):
        self.active = tuple(set(self.selection.elements()))

    @T.default("ui")
    def _default_ui(self):
        add_btn = W.Button(description="", icon="plus", layout={"width": "2.6em"})
        remove_btn = W.Button(description="", icon="minus", layout={"width": "2.6em"})
        set_btn = W.Button(description="", icon="circle", layout={"width": "2.6em"})

        add_btn.on_click(lambda *_: self.add())
        remove_btn.on_click(lambda *_: self.remove())
        set_btn.on_click(lambda *_: self.set_active())
        return W.HBox([add_btn, set_btn, remove_btn])


def lifecycle(old: Set, new: Set) -> Tuple[Set, Set]:
    exiting = old.difference(new)
    entering = new.difference(old)
    return exiting, entering
