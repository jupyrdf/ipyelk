# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from collections.abc import Iterable, Iterator

import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import BaseElement
from ..exceptions import RemovedAPI
from .tool import ResolvingTool

#: what ``paint``/``unpaint`` accept: one id, one element, or any iterable of them
Paintable = str | BaseElement | Iterable[str | BaseElement]


class Painter(ResolvingTool):
    """Temporary, view-only styling: CSS classes the browser adds to rendered
    elements without touching the model.

    Reached as ``viewer.painter``. ``styles`` maps an element id to the classes
    painted on it. The browser merges them into the rendered class list in every
    connected view, re-applies them after every later render (so a re-layout keeps
    them), and exported SVG shows them; ``properties.cssClasses`` and the ELK/model
    JSON never change, and clearing never removes a class the model set. Ids the
    model does not know are ignored in the browser; :meth:`missing_ids` reports them.

    A state-only tool: no ``run()``, no ``reports``, no re-layout. Every method
    assigns a new ``styles`` dict, so observers and the browser see each change.

    Attributes
    ----------
    styles: dict[str, tuple[str, ...]]
    element id -> CSS classes painted on it (order preserved, no duplicates).

    """

    # a browser update arrives with lists: TypedTuple validation stores tuples.
    # echo_update=False: a write is not echoed back to every frontend (the whole
    # dict travels on each call, and ipywidgets 8.1 echoes by default)
    styles = T.Dict(key_trait=T.Unicode(), value_trait=TypedTuple(T.Unicode())).tag(
        sync=True, echo_update=False
    )

    #: removed names raise :class:`~ipyelk.exceptions.DeprecatedAPIError` through 3.x
    cssClasses = RemovedAPI(
        "Painter.cssClasses was removed in ipyelk 3.0: it was an unfinished "
        "placeholder that painted nothing. Use painter.paint(ids, *css_classes) / "
        "painter.styles (id -> classes applied in the view only). No alias: this "
        "error is raised throughout 3.x."
    )
    marks = RemovedAPI(
        "Painter.marks was removed in ipyelk 3.0: it was an unfinished placeholder "
        "that painted nothing. Use painter.paint(ids_or_elements, *css_classes); "
        "painter.painted_ids lists what is painted. No alias: this error is raised "
        "throughout 3.x."
    )
    name = RemovedAPI(
        "Painter.name was removed in ipyelk 3.0: there is one painter per viewer "
        "(viewer.painter) holding an id -> classes mapping (painter.styles), so "
        "painters no longer need names. No alias: this error is raised throughout 3.x."
    )

    def paint(self, ids: Paintable, *css_classes: str) -> None:
        """Add ``css_classes`` to each of ``ids`` (a str is one id; elements are
        stored as their ``wire_id()``), keeping the classes already painted there.
        """
        styles = dict(self.styles)
        for el_id in _ids(ids):
            styles[el_id] = tuple(dict.fromkeys((*styles.get(el_id, ()), *css_classes)))
        self.styles = styles

    def unpaint(self, ids: Paintable, *css_classes: str) -> None:
        """Remove ``css_classes`` from each of ``ids``; with no classes, stop painting
        those ids altogether. Ids that are not painted are ignored.
        """
        styles = dict(self.styles)
        for el_id in _ids(ids):
            if el_id not in styles:
                continue
            kept = tuple(c for c in styles[el_id] if c not in css_classes)
            if not css_classes or not kept:
                del styles[el_id]
            else:
                styles[el_id] = kept
        self.styles = styles

    def clear(self) -> None:
        """Stop painting everything."""
        self.styles = {}

    @property
    def painted_ids(self) -> tuple[str, ...]:
        """The painted ids, in painting order."""
        return tuple(self.styles)

    def _held_ids(self) -> tuple[str, ...]:
        return self.painted_ids


def _ids(ids: Paintable) -> Iterator[str]:
    """One id per target: a ``str`` is one id (never its characters), an element is
    its ``wire_id()``, anything else is iterated.
    """
    targets: Iterable[str | BaseElement]
    targets = [ids] if isinstance(ids, (str, BaseElement)) else ids
    for target in targets:
        if isinstance(target, str):
            yield target
            continue
        yield target.wire_id()  # the id that the element keeps when indexed
