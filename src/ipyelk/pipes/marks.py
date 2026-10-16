# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import warnings

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    BaseElement,
    Document,
    ElementIndex,
    Node,
    Registry,
    elk_serialization,
)

#: the warning that reading or writing ``MarkIndex.context`` emits through 3.x
CONTEXT_DEPRECATED = (
    "MarkIndex.context is deprecated and will be removed in ipyelk 4.0: "
    "MarkIndex.document (an ipyelk.elements.Document) owns the ids, and "
    "nothing in ipyelk reads the Registry. Use index.document.resolve(id)."
)


class MarkIndex(W.DOMWidget):
    """The element index of a pipeline, which its stages and tools share.

    ``document`` owns the ids, and ``elements`` is ``document.elements``.
    ``elements`` and the deprecated ``context`` are properties, not traits:
    the constructor takes them, but ``observe`` does not see them.
    """

    document = T.Instance(Document, kw={})

    _root: Node | None = None
    _root_of: ElementIndex | None = None
    _context: Registry | None = None

    def __init__(
        self,
        elements: ElementIndex | None = None,
        context: Registry | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if elements is not None:
            self.elements = elements
        if context is not None:
            warnings.warn(CONTEXT_DEPRECATED, DeprecationWarning, stacklevel=2)
            self._context = context

    @property
    def elements(self) -> ElementIndex | None:
        """The id map of ``document``; ``None`` until something is indexed."""
        return self.document.elements

    @elements.setter
    def elements(self, elements: ElementIndex | None) -> None:
        self.document.elements = elements

    @property
    def context(self) -> Registry:
        """Deprecated: ``document`` owns the ids. Removed in ipyelk 4.0."""
        warnings.warn(CONTEXT_DEPRECATED, DeprecationWarning, stacklevel=2)
        if self._context is None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self._context = Registry()
        return self._context

    @context.setter
    def context(self, context: Registry) -> None:
        warnings.warn(CONTEXT_DEPRECATED, DeprecationWarning, stacklevel=2)
        self._context = context

    def to_id(self, element: BaseElement) -> str:
        return element.wire_id()

    def from_id(self, key: str) -> BaseElement:
        elements = self.elements
        if elements is None:
            raise ValueError("Can't have no elements!")
        element = elements.get(key)
        return element

    @property
    def root(self) -> Node:
        elements = self.elements
        if elements is None:
            raise ValueError("Root cannot be None after updating it!")
        if self._root_of is not elements:
            self._root, self._root_of = elements.root(), elements
        assert self._root is not None
        return self._root


class MarkElementWidget(W.DOMWidget):
    """An element tree plus the shared index and the pending ``flow``.

    ``value`` is synced with the browser only for a mark that a browser stage
    reads or writes (see :meth:`sync_value`). There it is written from both
    sides. A browser write is never sent back: ``echo_update=False`` stops the
    echo, and ``_should_send_property`` stops the re-serialized copy. Kernel
    writes are sent exactly once. ``flow`` and ``index`` are never synced: no
    browser code reads them.

    Known limitation: a second frontend attached to the same kernel used to
    learn browser-written values through the echo and no longer does.
    """

    #: synced per instance, see :meth:`sync_value`
    value = T.Instance(Node, allow_none=True).tag(
        echo_update=False, **elk_serialization
    )
    #: generation of the ``run`` request the browser last answered; ``0`` with
    #: an older extension build (see ``util.wait_for_answer``)
    gen = T.Int(0).tag(sync=True, echo_update=False)
    #: kernel only: no browser code reads it
    index = T.Instance(MarkIndex, kw={})
    flow: tuple[str, ...] = TypedTuple(T.Unicode(), kw={})

    #: the tree ``set_state`` last deserialized from the browser
    _browser_value: Node | None = None
    #: the synced trait names (``Widget.keys``), typed for mypy
    keys: list[str]

    def sync_value(self) -> MarkElementWidget:
        """Sync ``value`` with the browser from now on, and send it now.

        Only the marks that a browser stage reads or writes need ``value`` in
        the browser: the inlet and outlet of a ``SyncedInletPipe`` or
        ``SyncedOutletPipe``, and a viewer's ``source``. These call this
        method when they take the mark. A mark stays synced once it is.
        """
        if "value" not in self.keys:
            self.keys = [*self.keys, "value"]
            if self.comm is not None:
                self.send_state("value")
        return self

    def set_trait(self, name, value):
        """Remember which ``value`` came from the browser (``set_state`` holds
        ``_property_lock``), for ``_should_send_property``.
        """
        if name == "value" and name in self._property_lock:
            self._browser_value = value
        super().set_trait(name, value)

    def _should_send_property(self, key, value):
        """Never re-send a ``value`` the browser just wrote.

        The stock check always sends an elkjs-processed tree, whose
        re-serialization differs from the browser JSON. A new tree assigned by
        an observer while the lock is held is still sent.
        """
        if (
            key == "value"
            and key in self._property_lock
            and value is self._browser_value
        ):
            return False
        return super()._should_send_property(key, value)

    def record(self, *tags: str) -> tuple[str, ...]:
        """Add ``tags`` to the pending ``flow`` (order-preserving union).

        Writers must record rather than assign, which would overwrite what
        another writer left pending.
        """
        pending = list(self.flow)
        pending.extend(tag for tag in tags if tag not in pending)
        if len(pending) != len(self.flow):
            self.flow = tuple(pending)
        return self.flow

    def take(self) -> tuple[str, ...]:
        """Consume the pending ``flow``: return it and leave ``()`` behind.

        ``Pipeline.run`` takes at the start, so tags recorded mid-run stay
        pending for the next run.
        """
        taken, self.flow = self.flow, ()
        return taken

    def persist(self, rebuild_index: bool = False):
        """Fold ``value`` into the shared index.

        The index -- not ``value`` -- is the authority for the element
        hierarchy: hidden elements never survive serialization (see
        ``Node.model_dump``), so the index must be merged into, never rebuilt from, a
        value that has been through the browser.  ``rebuild_index`` is for the
        full Python-side hierarchy only (initially, or after adding elements);
        the merge path requires every element to already carry an id.
        """
        if rebuild_index or self.index.elements is None:
            self.build_index()
        elif self.value is not None:
            self.index.elements.update(ElementIndex.from_els(self.value))
        return self

    def build_index(self, *, assign_ids: bool = True) -> MarkIndex:
        """Index ``value`` in the shared ``Document``; by default pin the ids.

        The document writes the id that each element serializes with onto the
        elements that have none, so every later serialization emits the ids
        the index is keyed by, and ``persist`` can merge what comes back from
        the browser. Explicit ids are never changed. ``assign_ids=False``
        leaves ``id`` untouched so a caller can report or reject unassigned ids
        first (``ValidationPipe.fix_null_id``).
        """
        if self.value is None:
            self.index.elements = ElementIndex()
        else:
            self.index.document.index(self.value, assign_ids=assign_ids)
        return self.index

    def _repr_mimebundle_(self, **kwargs):
        from IPython.display import JSON, display

        if self.value:
            display(JSON(self.value.model_dump()))
