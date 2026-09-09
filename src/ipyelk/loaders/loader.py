# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

import traitlets as T
from typing_extensions import Self

from ..elements import Edge, Label, Node, Port, index
from ..elements import layout_options as opt
from ..tools import Tool

if TYPE_CHECKING:
    from ipyelk.elements.elements import BaseElement

    from ..pipes import MarkElementWidget

ROOT_OPTS: dict[str, str] = {
    opt.HierarchyHandling.identifier: str(opt.HierarchyHandling().value)
}
NODE_OPTS: dict[str, str] = {
    opt.NodeSizeConstraints.identifier: opt.NodeSizeConstraints().value,
}
PORT_OPTS: dict[str, str] = {}
LABEL_OPTS: dict[str, str] = {
    opt.NodeLabelPlacement.identifier: str(
        opt.NodeLabelPlacement(horizontal="center").value
    )
}
EDGE_OPTS: dict[str, str] = {}

SourceT = TypeVar("SourceT")


class Loader(Tool, Generic[SourceT]):
    default_node_opts = T.Dict(NODE_OPTS, allow_none=True)
    default_root_opts = T.Dict(ROOT_OPTS, allow_none=True)
    default_label_opts = T.Dict(LABEL_OPTS, allow_none=True)
    default_port_opts = T.Dict(PORT_OPTS, allow_none=True)
    default_edge_opts = T.Dict(EDGE_OPTS, allow_none=True)

    def load(self, source: SourceT, /) -> MarkElementWidget:
        """Build a diagram source from the loader's input type.

        Positional-only here so subclasses can name their input
        (``root=``, ``graph=``, ``data=``).
        """
        raise NotImplementedError("Subclasses should implement their behavior")

    def apply_layout_defaults(self, root: Node) -> Node:
        for el in index.iter_elements(root):
            if not el.layoutOptions:
                el.layoutOptions = self.get_default_opts(el)
        return root

    def get_default_opts(self, element: BaseElement) -> dict:
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
        return dict(**opts)

    def clear_defaults(self) -> Self:
        """Removes the current default layout options for the loader"""
        # `T.Dict(..., allow_none=True)` is typed as `dict[str, str]`, without the
        # `None`; `set_trait` keeps validation and observers and skips the stub.
        for name in (
            "default_node_opts",
            "default_root_opts",
            "default_label_opts",
            "default_port_opts",
            "default_edge_opts",
        ):
            self.set_trait(name, None)
        return self
