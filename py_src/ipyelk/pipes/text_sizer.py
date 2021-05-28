"""Widget to get text size from DOM
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..elements import Label, index
from ..styled_widget import StyledWidget
from . import flows as F
from .base import Pipe, SyncedPipe
from .util import wait_for_change


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
            return

        # make copy of source value?
        for el in index.iter_elements(self.source.value):
            if isinstance(el, Label):
                size(el)

        self.outlet.changes = tuple(set(*self.outlet.changes, *self.reports))
        return self.value


def size(label: Label):
    shape = label.properties.get_shape()
    if label.width is None:
        shape.width = 10 * len(label.text)
    if label.height is None:
        shape.height = 10


def size_nested_label(label: Label) -> Label:

    shape = label.properties.get_shape()
    width = label.width or shape.width or 0
    height = label.height or shape.height or 0

    for sublabel in label.labels or []:
        ls = size_nested_label(sublabel)
        layout_opts = sublabel.layoutOptions
        spacing = float(layout_opts.get("org.eclipse.elk.spacing.labelLabel", 0))
        width += ls.width or 0 + spacing
        height = max(height, ls.height or 0)

    label.width = width
    label.height = height
    return label


class BrowserTextSizer(SyncedPipe, StyledWidget, TextSizer):
    """Jupyterlab widget for getting rendered text sizes from the DOM"""

    _model_name = T.Unicode("ELKTextSizerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKTextSizerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    async def run(self):
        """Go measure some DOM"""
        # watch once
        if self.outlet is None:
            return

        # signal to browser and wait for done
        future_value = wait_for_change(self.outlet, "value")

        self.send({"action": "run"})

        # wait to return until
        # TODO if there is no change to the input text the
        # outlet value doesn't trigger
        await future_value
        self.outlet.persist()
