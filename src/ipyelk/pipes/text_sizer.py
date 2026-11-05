"""Widget to get text size from DOM"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
import os
import re
import weakref
from collections.abc import Iterator

import traitlets as T

from ..constants import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..elements import BaseElement, Edge, Label, Node, index
from ..elements.elements import is_hidden
from ..styled_widget import StyledWidget
from . import flows as F
from .base import Pipe, PipeStatus, SyncedPipe
from .util import browser_roundtrip


class TextSizer(Pipe):
    """simple rule of thumb width height guesser"""

    @T.default("observes")
    def _default_observes(self):
        return (
            F.Text.text,
            F.Text.size_css,
            F.Layout,
        )

    @T.default("reports")
    def _default_reports(self):
        return (F.Text.size,)

    async def run(self):
        if self.inlet.value is None:
            return None

        # make copy of source value?
        for el in index.iter_elements(self.inlet.value):
            if isinstance(el, Label):
                size(el)

        self.outlet.value = self.inlet.value
        self.outlet.flow = tuple({*self.outlet.flow, *self.reports})
        return self.outlet.value


def size(label: Label):
    shape = label.properties.get_shape()
    if label.width is None:
        shape.width = 10 * len(label.text)
    if label.height is None:
        shape.height = 10


def size_nested_label(label: Label) -> Label:
    """Size a label from its nested sublabels: widths (plus each sublabel's
    ``org.eclipse.elk.spacing.labelLabel``) add up, heights take the max.

    Currently has no caller in ``ipyelk``; kept as a rule-of-thumb sizer for
    nested labels.
    """
    shape = label.properties.get_shape()
    width = label.width or shape.width or 0
    height = label.height or shape.height or 0

    for sublabel in label.labels or []:
        ls = size_nested_label(sublabel)
        layout_opts = sublabel.layoutOptions
        spacing = float(layout_opts.get("org.eclipse.elk.spacing.labelLabel", 0))
        width += (ls.width or 0) + spacing
        height = max(height, ls.height or 0)

    label.width = width
    label.height = height
    return label


class BrowserTextSizer(SyncedPipe, StyledWidget, TextSizer):
    """JupyterLab widget for getting rendered text sizes from the DOM"""

    _model_name = T.Unicode("ELKTextSizerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKTextSizerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    timeout = T.Float(
        default_value=30.0,
        help=(
            "Seconds to wait for browser text measurements before giving up; "
            "0 waits forever."
        ),
    )

    def __init__(self, *args, **kwargs):
        # Sizes alone cannot say whether text edited while hidden was measured.
        # Weak references distinguish replacement labels with the same wire id.
        self._measured: dict[str, tuple[weakref.ReferenceType[Label], tuple]] = {}
        super().__init__(*args, **kwargs)

    def _size_key(self, label: Label) -> tuple:
        return (
            label.text,
            label.properties.cssClasses,
            self.namespaced_css,
            self._dom_classes,
        )

    def _visible_labels(self) -> Iterator[Label]:
        """Labels that survive the inlet's serialization, including nested ones."""

        def visit(el: BaseElement) -> Iterator[Label]:
            if el.properties.hidden:
                return
            if isinstance(el, Edge) and (is_hidden(el.source) or is_hidden(el.target)):
                return
            if isinstance(el, Label):
                shape = el.properties.shape
                # Match the browser: a fully specified shape needs no DOM.
                if not (shape and shape.width and shape.height):
                    yield el
            for label in el.labels:
                yield from visit(label)
            if isinstance(el, Node):
                for child in [*el.children, *el.ports, *el.edges]:
                    yield from visit(child)

        if self.inlet.value is not None:
            yield from visit(self.inlet.value)

    def check_dirty(self, flow: tuple[str, ...] | None = None) -> bool:
        if flow is None:
            flow = self.inlet.flow
        if super().check_dirty(flow):
            return True
        if not any(re.fullmatch(F.AnyHidden, tag) for tag in flow):
            return False
        for label in self._visible_labels():
            measured = self._measured.get(label.wire_id())
            previous = None if measured is None else measured[0]()
            if (
                measured is None
                or previous is not label
                or measured[1] != self._size_key(label)
            ):
                # A reveal needs sizing only for newly visible or changed text.
                self.status = PipeStatus.waiting()
                self.outlet.flow = tuple(dict.fromkeys((*flow, *self.reports)))
                return True
        return False

    async def run(self):
        """Go measure some DOM"""
        # watch once
        if self.outlet is None:
            return

        labels = [
            (weakref.ref(label), self._size_key(label))
            for label in self._visible_labels()
        ]
        # Discard removed/replaced labels, but retain valid sizes of hidden ones.
        value = self.inlet.value
        current = (
            {}
            if value is None
            else {el.wire_id(): el for el in index.iter_elements(value)}
        )
        self._measured = {
            key: measured
            for key, measured in self._measured.items()
            if measured[0]() is current.get(key) and measured[0]() is not None
        }

        for ref, _key in labels:
            label = ref()
            if label is not None:
                self._measured.pop(label.wire_id(), None)

        # In-place edits keep the same inlet object, so traitlets sends no
        # change. Every sizing request must read the current tree in the browser.
        self.inlet.send_state("value")

        # signal to browser (re-sending until a frontend answers) and wait
        # for done, browser error, or deadline
        try:
            await browser_roundtrip(self, timeout=self.timeout or None)
        except asyncio.TimeoutError:
            if not (
                os.environ.get("IPYELK_TESTING") or os.environ.get("IPYELK_NO_BROWSER")
            ):
                raise
            await TextSizer.run(self)
        else:
            # Check before persist, which merges the reply into the user's tree.
            unchanged = [
                (ref, key)
                for ref, key in labels
                if (label := ref()) is not None and self._size_key(label) == key
            ]
            self.outlet.persist()
            for ref, key in unchanged:
                label = ref()
                if (
                    label is not None
                    and self._size_key(label) == key
                    and label.width is not None
                    and label.height is not None
                ):
                    if label.width or label.height or not label.text:
                        self._measured[label.wire_id()] = (ref, key)
