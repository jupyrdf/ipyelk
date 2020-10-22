# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import re
from typing import Dict, Hashable, List

import ipywidgets as W
import traitlets as T

from ..elk_model import ElkGraphElement


class LayoutOptionWidget(W.VBox):
    identifier: Hashable = None
    metadata_provider: str = None
    applies_to: List[ElkGraphElement] = None
    group: str = None

    value = T.Unicode()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_value()

    def _ipython_display_(self, **kwargs):
        if not self.children:
            self.children = self._ui()
        super()._ipython_display_(**kwargs)

    def _ui(self) -> List[W.Widget]:
        raise NotImplementedError(
            "Subclasses should implement their specific UI Controls"
        )

    def _update_value(self):
        pass  # expecting subclasses to override


class SpacingOptionWidget(LayoutOptionWidget):
    spacing = T.Float(default_value=10, min=0)
    _slider_description: str = ""

    def _ui(self) -> List[W.Widget]:
        slider = W.FloatSlider(description=self._slider_description, min=0)

        T.link((self, "spacing"), (slider, "value"))

        return [slider]

    @T.observe("spacing")
    def _update_value(self, change: T.Bunch = None):
        self.value = str(self.spacing)


class OptionsWidget(W.Accordion, LayoutOptionWidget):
    options: List[LayoutOptionWidget] = T.List(T.Instance(LayoutOptionWidget))
    value: Dict = T.Dict()

    @T.observe("options")
    def _update_options(self, change: T.Bunch = None):
        if change and change.old is not T.Undefined:
            for old_option in change.old:
                old_option.unobserve(self._update_value, "value")
        for option in self.options:
            option.observe(self._update_value, "value")

        if self.children:
            self.children = self.options

    def _ui(self):
        # loop over options and build their UI if required
        for i, option in enumerate(self.options):
            if not option.children:
                option.children = option._ui()

            title = re.sub(r"(\w)([A-Z])", r"\1 \2", option.__class__.__name__)
            self.set_title(i, title)
        return self.options

    def _update_value(self, change: T.Bunch = None):
        value = {}
        for option in self.options:
            value[option.identifier] = option.value
        self.value = value
