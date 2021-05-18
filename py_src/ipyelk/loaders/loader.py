# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict, Optional

import traitlets as T

from ipyelk.elements.elements import BaseElement

from ..elements import Edge, Label, Node, Port, index
from ..elements import layout_options as opt
from ..pipes import MarkElementWidget
from ..tools import Tool

ROOT_OPTS: Dict[str, str] = {
    opt.HierarchyHandling.identifier: opt.HierarchyHandling().value
}
NODE_OPTS: Dict[str, str] = {
    opt.NodeSizeConstraints.identifier: opt.NodeSizeConstraints().value,
}
PORT_OPTS: Dict[str, str] = {}
LABEL_OPTS: Dict[str, str] = {
    opt.NodeLabelPlacement.identifier: opt.NodeLabelPlacement(horizontal="center").value
}
EDGE_OPTS: Dict[str, str] = {}


class Loader(Tool):
    default_node_opts: Optional[Dict[str, str]] = T.Dict(NODE_OPTS, allow_none=True)
    default_root_opts: Optional[Dict[str, str]] = T.Dict(ROOT_OPTS, allow_none=True)
    default_label_opts: Optional[Dict[str, str]] = T.Dict(LABEL_OPTS, allow_none=True)
    default_port_opts: Optional[Dict[str, str]] = T.Dict(PORT_OPTS, allow_none=True)
    default_edge_opts: Optional[Dict[str, str]] = T.Dict(EDGE_OPTS, allow_none=True)

    def load(self) -> MarkElementWidget:
        raise NotImplementedError("Subclasses should implement their behavior")

    def apply_layout_defaults(self, root: Node) -> Node:
        for el in index.iter_elements(root):
            if not el.layoutOptions:
                el.layoutOptions = self.get_default_opts(el)
        return root

    def get_default_opts(self, element: BaseElement) -> Dict:
        if isinstance(element, Node):
            if element.get_parent() is None:
                opts = self.default_root_opts
            else:
                opts = self.default_node_opts
        elif isinstance(element, Port):
            opts = self.default_port_opts
        elif isinstance(element, Label):
            opts = self.default_label_opts
        elif isinstance(element, Edge):
            opts = self.default_edge_opts
        if opts is None:
            return dict()
        else:
            return dict(**opts)

    def clear_defaults(self) -> "Loader":
        """Removes the current default layout options for the loader"""
        self.default_node_opts = None
        self.default_root_opts = None
        self.default_label_opts = None
        self.default_port_opts = None
        self.default_edge_opts = None
        return self
