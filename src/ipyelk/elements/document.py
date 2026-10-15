# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The owner of the element ids of one diagram (#160)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, NamedTuple

from ..exceptions import NotFoundError
from .index import ElementIndex

if TYPE_CHECKING:
    from .elements import BaseElement


class Resolved(NamedTuple):
    """The element that an id names.

    ``via_slack`` is ``True`` when the id is that of a slack port: the port that
    the projection adds to the nearest visible ancestor of a hidden element, so
    that an edge to the hidden element keeps an endpoint. ``element`` is then the
    hidden element.
    """

    element: BaseElement
    via_slack: bool = False


class Document:
    """The ids of one element tree, and the elements that they name.

    :meth:`index` gives each element that has no ``id`` the id that it
    serializes with (``wire_id``), so the id that the browser sees is the id
    that the element keeps. No context manager and no global state take part:
    this replaces the ``Registry`` stack. ``MarkIndex.document`` is the
    document of a pipeline, which every stage and tool of the pipeline shares.

    .. code-block:: python

        doc = Document(root)
        doc.resolve("n1")  # Resolved(element=..., via_slack=False), or None
        doc.missing(["n1", "typo"])  # ("typo",)
        list(doc.lookup(["n1"]))  # the elements; strict=False skips unknown ids
    """

    def __init__(self, *roots: BaseElement) -> None:
        #: id to element, ``None`` until :meth:`index` runs
        self.elements: ElementIndex | None = None
        #: slack port id to the id of the hidden element that the port stands for
        self.slack: dict[str, str] = {}
        if roots:
            self.index(*roots)

    def index(self, *roots: BaseElement, assign_ids: bool = True) -> ElementIndex:
        """Map the id of every element under ``roots`` to the element.

        :param assign_ids: when True (default), write the id onto each element
            that has none. ``False`` leaves ``id`` as it is, so a caller can
            report the elements without one first (``ValidationPipe``).
        """
        elements = ElementIndex.from_els(*roots)
        if assign_ids:
            for key, el in elements.items():
                if el.id is None:
                    el.id = key
        self.elements = elements
        return elements

    def resolve(self, el_id: str) -> Resolved | None:
        """The element that ``el_id`` names, or ``None`` for an unknown id.

        A slack port id resolves to its hidden element, with ``via_slack``.
        """
        if self.elements is None:
            return None
        hidden = self.slack.get(el_id)
        known = self.elements.elements
        if hidden is not None and hidden in known:
            return Resolved(known[hidden], via_slack=True)
        element = known.get(el_id)
        return None if element is None else Resolved(element)

    def missing(self, ids: Iterable[str]) -> tuple[str, ...]:
        """The ids of ``ids`` that do not resolve, in order."""
        return tuple(el_id for el_id in ids if self.resolve(el_id) is None)

    def lookup(
        self, ids: Iterable[str], *, strict: bool = True
    ) -> Iterator[BaseElement]:
        """The elements that ``ids`` name, in order.

        :param strict: when True (default), an id that does not resolve raises
            :class:`~ipyelk.exceptions.NotFoundError` naming it; when False such
            ids are skipped (:meth:`missing` reports them).
        """
        for el_id in ids:
            found = self.resolve(el_id)
            if found is not None:
                yield found.element
            elif strict:
                raise NotFoundError(f"Element with id:{el_id} not in index")
