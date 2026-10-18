"""The ELK element kinds that a layout option applies to.

``LayoutOptionWidget.applies_to`` names these tag classes. They have no fields: the
elements themselves are :mod:`ipyelk.elements`. ``ipyelk`` 2.x had generated ELK JSON
data classes here, which nothing used. Their names raise
:class:`~ipyelk.exceptions.DeprecatedImportError` throughout 3.x.
"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from ...exceptions import DeprecatedImportError


class ElkGraphElement:
    """Any ELK graph element."""


class ElkNode(ElkGraphElement):
    """An ELK node, the ``NODES`` target of an option."""


class ElkPort(ElkGraphElement):
    """An ELK port, the ``PORTS`` target of an option."""


class ElkEdge(ElkGraphElement):
    """An ELK edge, the ``EDGES`` target of an option."""


class ElkLabel(ElkGraphElement):
    """An ELK label, the ``LABELS`` target of an option."""


_GONE = "No alias: this error is raised throughout 3.x."
_DATACLASS = (
    "it was a generated ELK JSON data class that nothing in ipyelk used, and nothing "
    "replaces it. Build graphs from ipyelk.elements.Node, Port, Edge and Label, and load "
    "ELK JSON with ipyelk.elements.convert_elkjson or from_wire."
)
_CONVERTER = (
    "it converted the generated ELK JSON data classes, which nothing in ipyelk used, and "
    "nothing replaces it. Load ELK JSON with ipyelk.elements.convert_elkjson or "
    "from_wire."
)
_SENTINEL = "it was a sentinel that nothing in ipyelk used, and nothing replaces it."

#: removed names raise :class:`~ipyelk.exceptions.DeprecatedImportError` through 3.x
_REMOVED = {
    name: f"ipyelk.elements.layout_options.model.{name} was removed in ipyelk 3.0: "
    f"{reason} {_GONE}"
    for names, reason in [
        (
            [
                "Elk",
                "ElkProperties",
                "ELKConstructorArguments",
                "ELKLayoutArguments",
                "ElkPoint",
                "ElkShape",
                "ElkEdgeSection",
                "ElkExtendedEdge",
                "ElkPrimitiveEdge",
                "ElkSerializable",
            ],
            _DATACLASS,
        ),
        (
            [
                "from_bool",
                "from_dict",
                "from_float",
                "from_int",
                "from_list",
                "from_none",
                "from_str",
                "from_union",
                "to_class",
                "to_float",
            ],
            _CONVERTER,
        ),
        (["ElkRoot", "ElkNullElement"], _SENTINEL),
        (["strip_none"], "it moved. Import strip_none from ipyelk.util."),
    ]
    for name in names
}


def __getattr__(name: str) -> object:
    if name in _REMOVED:
        raise DeprecatedImportError(_REMOVED[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
