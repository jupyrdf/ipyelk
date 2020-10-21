# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
from typing import Dict, Hashable, Optional

import ipywidgets as W
import traitlets as T

from .diagram import ElkDiagram, ElkLabel, ElkNode
from .schema import ElkSchemaValidator
from .styled_widget import StyledWidget
from .toolbar import Toolbar
from .trait_types import Schema


class ElkTransformer(W.Widget):
    """ Transform data into the form required by the ElkDiagram. """

    _nodes: Optional[Dict[Hashable, ElkNode]] = None
    source = T.Dict()
    value = Schema(ElkSchemaValidator)
    _version: str = "v1"
    _task: asyncio.Task = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.refresh()

    async def transform(self) -> ElkNode:
        """Generate elk json"""
        return ElkNode(**self.source)

    @T.default("value")
    def _default_value(self):
        return {"id": "root"}

    async def _refresh(self):
        root_node = await self.transform()
        value = root_node.to_dict()

        # forces redraw on the frontend by creating to new label
        labels = value.get("labels", [])
        labels.append(ElkLabel(id=str(id(value))).to_dict())

        value["labels"] = labels
        self.value = value

    @T.observe("source")
    def refresh(self, change: T.Bunch = None):
        """Method to update this transform's value by scheduling the
        transformation task on event loop
        """
        self.log.debug("Refreshing elk transformer")
        # remove previous refresh task if still pending
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._refresh())

    def from_id(self, element_id: str) -> Hashable:
        """Use the elk identifiers to find original objects"""
        return element_id

    def to_id(self, item: Hashable) -> str:
        """Use original objects to find elk id"""
        return item

    def connect(self, view: ElkDiagram) -> T.link:
        """Connect the output value of this transformer to a diagram"""
        return T.dlink((self, "value"), (view, "value"))


class Elk(W.VBox, StyledWidget):
    """ An Elk diagramming widget """

    transformer: ElkTransformer = T.Instance(ElkTransformer)
    diagram: ElkDiagram = T.Instance(ElkDiagram)
    selected = T.Tuple()
    hovered = T.Any(allow_none=True, default_value=None)
    toolbar: Toolbar = T.Instance(Toolbar, kw={})

    _data_link: T.dlink = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_data_link()
        self._update_children()
        self.add_class("jp-ElkApp")

    def _set_arrows_opacity(self, value):
        style = self.style
        css_selector = " path.edge.arrow"

        arrow_style = style.get(css_selector, {})
        arrow_style["opacity"] = str(value)

        style[css_selector] = arrow_style
        self.style = style.copy()
        # TODO should not need to trigger update this way but the observer isn't firing
        self._update_style()

    def hide_arrows(self):
        self._set_arrows_opacity(0)

    def show_arrows(self):
        self._set_arrows_opacity(1)

    @T.default("diagram")
    def _default_diagram(self):
        return ElkDiagram()

    @T.default("transformer")
    def _default_transformer(self):
        return ElkTransformer()

    @T.observe("diagram", "transformer")
    def _update_data_link(self, *_):
        if isinstance(self._data_link, T.link):
            self._data_link.unlink()
            self._data_link = None
        if self.transformer and self.diagram:
            self._data_link = T.dlink(
                (self.transformer, "value"), (self.diagram, "value"),
            )

    @T.observe("diagram")
    def _update_children(self, change: T.Bunch = None):
        self.children = [self.diagram, self.toolbar]

        if change:
            # uninstall old observers
            safely_unobserve(change.old, "selected")
            safely_unobserve(change.old, "hovered")

        if self.diagram:  # also change.new
            self.diagram.observe(self._handle_diagram_selected, "selected")
            self.diagram.observe(self._handle_diagram_hovered, "hovered")

    def _handle_diagram_selected(self, change: T.Bunch):
        items = []
        if change.new:
            items = [self.transformer.from_id(s) for s in change.new]
        if items != self.selected:
            self.selected = items

    def _handle_diagram_hovered(self, change: T.Bunch):
        _id = self.transformer.from_id(change.new)
        if _id != self.hovered:
            self.hovered = _id

    @T.observe("selected")
    def _update_selected(self, change: T.Bunch):
        if not self.diagram:
            return

        # transform selected nodes into ids and test if new ids
        ids = [self.transformer.to_id(s) for s in self.selected]
        if self.diagram.selected != ids:
            self.diagram.selected = ids

    @T.observe("hovered")
    def _update_hover(self, change: T.Bunch):
        if not self.diagram:
            return

        # transform hovered nodes into elk id
        self.diagram.hover = self.transformer.to_id(self.hovered)

    def refresh(self):
        self.transformer.refresh()


def safely_unobserve(item, handler):
    if hasattr(item, "unobserve"):
        item.unobserve(handler=handler)
