# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T

from .diagram import ElkDiagram
from .diagram.elk_model import ElkNullElement
from .styled_widget import StyledWidget
from .toolbar import Toolbar
from .transform import ElkTransformer


class Elk(W.VBox, StyledWidget):
    """ An Elk diagramming widget """

    transformer: ElkTransformer = T.Instance(ElkTransformer)
    diagram: ElkDiagram = T.Instance(ElkDiagram)
    selected = T.Tuple()
    hovered = T.Any(allow_none=True, default_value=ElkNullElement)
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
                (self.transformer, "value"),
                (self.diagram, "value"),
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
        try:
            _id = self.transformer.from_id(change.new)
        except ValueError:  # TODO introduce custom ipyelk exceptions
            _id = ElkNullElement
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
        if not self.diagram or self.hovered is ElkNullElement:
            return

        # transform hovered nodes into elk id
        try:
            self.diagram.hover = self.transformer.to_id(self.hovered)
        except ValueError:  # TODO introduce custom ipyelk exceptions
            # okay not to pass the hovered state to the diagram?
            pass

    def refresh(self):
        self.transformer.refresh()


def safely_unobserve(item, handler):
    if hasattr(item, "unobserve"):
        item.unobserve(handler=handler)
