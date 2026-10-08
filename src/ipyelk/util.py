# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from .elements.layout_options.model import strip_none


def close_widget(widget) -> None:
    """Close a widget with its ``layout`` and ``style`` widgets, if it has them."""
    widget.close()
    for name in ("layout", "style"):
        part = widget._trait_values.get(name)
        if hasattr(part, "close"):
            part.close()


def own_layout(widget, kwargs: dict):
    """The ``layout`` a widget built for itself, unless one was passed in."""
    layout = widget._trait_values.get("layout")
    given = kwargs.get("layout")
    return None if given is layout and hasattr(given, "close") else layout


def close_own_layout(widget) -> None:
    """Close the ``layout`` recorded by ``own_layout``, if it is still in use."""
    layout = getattr(widget, "_own_layout", None)
    if layout is not None and widget._trait_values.get("layout") is layout:
        layout.close()


def close_tree(widget) -> None:
    """Close ``widget`` and its ``children``, with their layout and style widgets."""
    for child in getattr(widget, "children", ()):
        close_tree(child)
    close_widget(widget)


def safely_unobserve(item, handler):
    if hasattr(item, "unobserve"):
        item.unobserve(handler=handler)


def to_dict(obj):
    """Shim function to convert obj to a dictionary"""
    if obj is None:
        data = {}
    elif isinstance(obj, dict):
        data = obj
    elif hasattr(obj, "to_dict"):
        data = obj.to_dict()
    elif hasattr(obj, "model_dump"):
        data = obj.model_dump()
    else:
        raise TypeError("Unable to convert to dictionary")
    return data


def merge(d1: dict | None, d2: dict | None) -> dict:
    """Merge two dictionaries while first testing if either are `None`.
    The first dictionary's keys take precedence over the second dictionary.
    If the final merged dictionary is empty `None` is returned.

    :param d1: primary dictionary
    :type d1: dict | None
    :param d2: secondary dictionary
    :type d2: dict | None
    :return: merged dictionary
    :rtype: dict
    """
    d1 = to_dict(d1)
    d2 = to_dict(d2)

    cl1 = d1.get("cssClasses") or ""
    cl2 = d2.get("cssClasses") or ""
    cl = " ".join(sorted(set([*cl1.split(), *cl2.split()]))).strip()

    value = {**strip_none(d2), **strip_none(d1)}  # right most wins if duplicated keys

    # if either had cssClasses, update that
    if cl:
        value["cssClasses"] = cl

    return value


def listed(values: list | None) -> list:
    """Checks if incoming `values` is None then either returns a new list or
    original value.

    :param values: list of values
    :type values: list | None
    :return: list of values or empty list
    :rtype: list
    """
    if values is None:
        return []
    return values
