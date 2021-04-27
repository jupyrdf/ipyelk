"""Widget to get text size from DOM
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T

from ..._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ...elements import Label
from ...elements.serialization import iter_elements
from ...styled_widget import StyledWidget
from ..base import Pipe, SyncedPipe
from ..util import wait_for_change


class TextSizer(Pipe):
    """simple rule of thumb width height guesser"""

    async def run(self):
        if self.value is None:
            return

        # make copy of source value?
        for el in iter_elements(self.source.value):
            if isinstance(el, Label):
                size(el)
        for el in iter_elements(self.source.value):
            if isinstance(el, Label):
                size(el)
        return self.value


def size(label: Label):
    shape = label.properties.get_shape()()
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


class BrowserTextSizer(SyncedPipe, StyledWidget):
    """Jupyterlab widget for getting rendered text sizes from the DOM"""

    _model_name = T.Unicode("ELKTextSizerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKTextSizerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    timeout = T.Float(default_value=0.1, min=0)
    max_size = T.Int(default_value=100)

    async def run(self):
        """Go measure some dom"""
        # TODO trigger message

        # watch once
        if self.value is None:
            return

        future_value = wait_for_change(self.value, "value")
        self.send({})
        # signal to browser and wait for done

        # wait to return until
        await future_value
        return self.value
