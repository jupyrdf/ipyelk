# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    BaseElement,
    ElementIndex,
    Node,
    Registry,
    elk_serialization,
)


class MarkIndex(W.DOMWidget):
    elements = T.Instance(ElementIndex, allow_none=True)
    context = T.Instance(Registry, kw={})

    _root: Node | None = None
    #: the last browser-written tree ``MarkElementWidget.persist`` merged in;
    #: lets ``ValidationPipe`` recognise that copy if a caller swaps it into
    #: the inlet (2.1.x ``Diagram.refresh`` did) rather than the user's root
    merged_from: Node | None = None

    def to_id(self, element: BaseElement):
        return element.get_id()

    def from_id(self, key: str) -> BaseElement:
        elements = self.elements
        if elements is None:
            raise ValueError("Can't have no elements!")
        element = elements.get(key)
        return element

    @property
    def root(self) -> Node:
        if self._root is None:
            self._update_root()
        if self._root is None:
            raise ValueError("Root cannot be None after updating it!")
        return self._root

    @T.observe("elements")
    def _update_root(self, change: T.Bunch | None = None):
        self._root = None
        if self.elements:
            self._root = self.elements.root()


class MarkElementWidget(W.DOMWidget):
    """A synced element tree plus the shared index and the pending ``flow``.

    ``value`` is written from both sides: the kernel assigns a new tree, and
    the browser writes back the measured or laid-out tree (text sizer, elkjs).
    A browser write must not be re-sent: ipywidgets would otherwise echo the
    raw JSON to every frontend *and* send a second ``update`` carrying the
    re-serialised pydantic tree (which differs from the browser JSON by
    elkjs-internal keys), and each arrival re-renders the diagram.  So
    ``value`` is tagged ``echo_update=False`` and ``_should_send_property``
    suppresses the second send while the browser's property lock is held.
    Kernel-initiated writes have an empty lock and are sent exactly once.

    Known limitation: a second frontend attached to the same kernel used to
    learn browser-written values through the echo and no longer does.
    """

    value = T.Instance(Node, allow_none=True).tag(
        sync=True, echo_update=False, **elk_serialization
    )
    #: generation of the ``run`` request the browser answered when it last
    #: wrote ``value`` (written in the same ``save_changes``); ``0`` until a
    #: frontend answers, or forever with an older extension build.  Lets
    #: ``browser_roundtrip`` tell a fresh answer from one to an abandoned run,
    #: and is the change the kernel sees when the answered ``value`` is
    #: identical to the previous one (``util.wait_for_answer``).
    gen = T.Int(0).tag(sync=True, echo_update=False)
    index = T.Instance(MarkIndex, kw={}).tag(sync=True, **W.widget_serialization)

    flow: tuple[str, ...] = TypedTuple(T.Unicode(), kw={}).tag(sync=True)

    def _should_send_property(self, key, value):
        """Never re-send a ``value`` the browser just wrote.

        ``Widget.set_state`` holds ``_property_lock`` while trait notifications
        fire, so ``key in self._property_lock`` means this change *is* the
        browser's write.  The stock check compares the re-serialised value with
        the browser JSON and sends when they differ, which they always do for
        an elkjs-processed tree; the browser already renders its own object,
        so that send is pure churn.
        """
        if key == "value" and key in self._property_lock:
            return False
        return super()._should_send_property(key, value)

    def record(self, *tags: str) -> tuple[str, ...]:
        """Add ``tags`` to the pending ``flow`` (order-preserving union).

        Writers (tools, ``Diagram``) must *record* rather than assign: an
        assignment overwrites whatever another writer left pending, and a
        tag that was recorded while a run was in flight would be wiped by
        that run's completion.
        """
        pending = list(self.flow)
        pending.extend(tag for tag in tags if tag not in pending)
        if len(pending) != len(self.flow):
            self.flow = tuple(pending)
        return self.flow

    def take(self) -> tuple[str, ...]:
        """Consume the pending ``flow``: return it and leave ``()`` behind.

        A run takes the flow when it *starts*, so anything recorded while it
        runs stays pending for the next run instead of being erased when
        this one completes (``Pipeline.run``).
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
            self.index.merged_from = self.value
        return self

    def build_index(self, *, assign_ids: bool = True) -> MarkIndex:
        """Index ``value``; by default pin the resulting ids onto the elements.

        The index's ``Registry`` assigns ids to elements that have none; writing
        them back is what lets every later serialization -- which runs outside
        the Registry -- emit the ids the index is keyed by, so ``persist`` can
        merge what comes back from the browser.  Explicit ids are never changed.
        ``assign_ids=False`` leaves ``id`` untouched so a caller can report or
        reject unassigned ids first (``ValidationPipe.fix_null_id``).
        """
        if self.value is None:
            index = ElementIndex()
        else:
            with self.index.context:
                index = ElementIndex.from_els(self.value)
            if assign_ids:
                for key, el in index.items():
                    if el.id is None:
                        el.id = key
        self.index.elements = index
        self.index.merged_from = None
        return self.index

    def _repr_mimebundle_(self, **kwargs):
        from IPython.display import JSON, display

        if self.value:
            display(JSON(self.value.model_dump()))
