# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import logging
from typing import Dict, Hashable, Optional

import ipywidgets as W
import traitlets as T

from .diagram import ElkDiagram, ElkLabel, ElkNode
from .schema import ElkSchemaValidator
from .styled_widget import StyledWidget
from .trait_types import Schema

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


class Elk(W.VBox, StyledWidget):
    """ An Elk diagramming widget """

    transformer: ElkTransformer = T.Instance(ElkTransformer)
    diagram: ElkDiagram = T.Instance(ElkDiagram)

    _data_link: T.dlink = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_data_link()
        self._update_children()

    def _set_arrows_opacity(self, value):
        style = self.style
        css_selector = " path.edge.arrow"

        arrow_style = style.get(css_selector, {})
        arrow_style["opacity"] = str(value)

        style[css_selector] = arrow_style
        self.style = style.copy()

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
    def _update_children(self, *_):
        self.children = [self.diagram]

    def refresh(self):
        self.transformer.refresh()
