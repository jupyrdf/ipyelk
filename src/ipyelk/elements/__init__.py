# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from ..exceptions import DeprecatedImportError
from .common import EMPTY_SENTINEL, LayoutOptions, from_wire
from .document import Document, Resolved
from .elements import (
    BaseElement,
    Edge,
    EdgeProperties,
    ElementMetadata,
    HierarchicalElement,
    Label,
    LabelProperties,
    Node,
    NodeProperties,
    Port,
    PortProperties,
    exclude_hidden,
    exclude_layout,
)
from .extended import Compartment, Partition, Record
from .index import (
    EdgeReport,
    ElementIndex,
    HierarchicalIndex,
    IDReport,
    VisIndex,
    iter_edges,
    iter_elements,
    iter_hierarchy,
    iter_labels,
    iter_visible,
)
from .registry import Registry
from .serialization import convert_elkjson, elk_serialization, symbol_serialization
from .shapes import EdgeShape, ElementShape, LabelShape, NodeShape, PortShape
from .symbol import EndpointSymbol, Symbol, SymbolSpec

# a module ``__getattr__`` can only live in the package module itself
#: removed class names raise :class:`~ipyelk.exceptions.DeprecatedImportError` through 3.x
_REMOVED = {  # ruff: ignore[non-empty-init-module]
    name: (
        f"ipyelk.elements.{name} was removed in ipyelk 3.0: Mark and MarkFactory "
        "served the networkx transformer that ipyelk 2.0 removed (#90), and nothing "
        "used them since. To use one fragment in several places, copy it with "
        "Node.clone(prefix); to load a networkx graph, use ipyelk.from_nx or "
        "ipyelk.loaders.NXLoader. No alias: this error is raised throughout 3.x."
    )
    for name in ("Mark", "MarkFactory")
}


def __getattr__(name: str) -> object:
    if name in _REMOVED:
        raise DeprecatedImportError(_REMOVED[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "EMPTY_SENTINEL",
    "BaseElement",
    "Compartment",
    "Document",
    "Edge",
    "EdgeProperties",
    "EdgeReport",
    "EdgeShape",
    "ElementIndex",
    "ElementMetadata",
    "ElementShape",
    "EndpointSymbol",
    "HierarchicalElement",
    "HierarchicalIndex",
    "IDReport",
    "Label",
    "LabelProperties",
    "LabelShape",
    "LayoutOptions",
    "Node",
    "NodeProperties",
    "NodeShape",
    "Partition",
    "Port",
    "PortProperties",
    "PortShape",
    "Record",
    "Registry",
    "Resolved",
    "Symbol",
    "SymbolSpec",
    "VisIndex",
    "convert_elkjson",
    "elk_serialization",
    "exclude_hidden",
    "exclude_layout",
    "from_wire",
    "iter_edges",
    "iter_elements",
    "iter_hierarchy",
    "iter_labels",
    "iter_visible",
    "symbol_serialization",
]
