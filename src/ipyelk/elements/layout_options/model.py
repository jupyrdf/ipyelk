"""The ELK element kinds that a layout option applies to.

``LayoutOptionWidget.applies_to`` names these tag classes. They have no fields: the
elements themselves are :mod:`ipyelk.elements`. ``ipyelk`` 2.x had generated ELK JSON
data classes here, which nothing used. Their names raise
:class:`~ipyelk.exceptions.DeprecatedImportError` throughout 3.x. ``strip_none``
moved to :func:`ipyelk.util.strip_none`: its old name warns and keeps working.
"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import warnings

from ...exceptions import DeprecatedImportError
from ...util import strip_none as _strip_none


class ElkGraphElement:
    """Any ELK graph element."""

    #: the class of :mod:`ipyelk.elements` that makes this kind of element
    _element = "Node, Port, Edge or Label"

    def __init__(self, *args: object, **kwargs: object) -> None:
        name = type(self).__name__
        msg = (
            f"{name} is a tag class with no fields: it names the kind of element that"
            " a layout option applies to. To make an element, use"
            f" ipyelk.elements.{self._element}."
        )
        raise TypeError(msg)


class ElkNode(ElkGraphElement):
    """An ELK node, the ``NODES`` target of an option."""

    _element = "Node"


class ElkPort(ElkGraphElement):
    """An ELK port, the ``PORTS`` target of an option."""

    _element = "Port"


class ElkEdge(ElkGraphElement):
    """An ELK edge, the ``EDGES`` target of an option."""

    _element = "Edge"


class ElkLabel(ElkGraphElement):
    """An ELK label, the ``LABELS`` target of an option."""

    _element = "Label"


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
    ]
    for name in names
}


def __getattr__(name: str) -> object:
    if name == "strip_none":  # it moved, so it warns and keeps working
        warnings.warn(
            f"{__name__}.strip_none is deprecated: import strip_none from ipyelk.util."
            " ipyelk 4.0 removes this alias.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _strip_none
    if name in _REMOVED:
        raise DeprecatedImportError(_REMOVED[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
