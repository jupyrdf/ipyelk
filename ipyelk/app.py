import ipywidgets as W
import logging
import traitlets as T

from typing import List, Dict, Hashable, Optional

from .diagram import ElkDiagram, ElkLabel, ElkNode
from .schema import ElkSchemaValidator
from .styled_widget import StyledWidget
from .trait_types import Schema
from .tools import Toolbar

logger = logging.getLogger(__name__)


class ElkTransformer(W.Widget):
    """ Transform data into the form required by the ElkDiagram. """

    _nodes: Optional[Dict[Hashable, ElkNode]] = None
    source = T.Dict()
    value = Schema(ElkSchemaValidator)
    _version: str = "v1"

    def to_dict(self):
        """Generate elk json"""
        return self.source

    @T.default("value")
    def _default_value(self):
        return {"id": "root"}

    @T.observe("source")
    def refresh(self, change: T.Bunch = None) -> Dict:
        """Method to update this transform's value"""
        logger.debug("Refreshing elk transformer")
        self.value = self.to_dict()
        labels = self.value.get("labels", [])

        labels.append(ElkLabel(id=str(id(self.value))).to_dict())

        self.value["labels"] = labels

        return self.value

    def from_id(self, element_id:str)->Hashable:
        """Use the elk identifiers to find original objects"""
        return element_id

    def to_id(self, item:Hashable)->str:
        """Use original objects to find elk id"""
        return item


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
    def _update_children(self, change:T.Bunch=None):
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

        # transform selected nodes into ids and test if resulting list of element ids is new
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
