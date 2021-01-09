# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import re
from typing import Dict, Hashable, List, Type, Union

import ipywidgets as W
import traitlets as T

from ..elk_model import ElkGraphElement


class LayoutOptionWidget(W.VBox):
    identifier: Hashable = None
    metadata_provider: str = None
    applies_to: List[ElkGraphElement] = None
    group: str = None
    title: str = None  # optional title for UI purposes

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

    @classmethod
    def matches(cls, elk_type: Type[ElkGraphElement]):
        """Checks if this LayoutOption applies to given ElkGraphElement type"""
        if cls.applies_to is None:
            return False
        if isinstance(cls.applies_to, (tuple, list)):
            is_valid = elk_type in cls.applies_to
            # if not is_valid and elk_type is ElkNode:
            #     # options with applies_to "parents" should match ElkNode
            #     is_valid = cls.matches("parents")
            return is_valid
        return elk_type == cls.applies_to


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
    identifier = T.Any()
    options: List["OptionsWidget"] = T.List()
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

            title = option.title
            if title is None:
                title = re.sub(r"(\w)([A-Z])", r"\1 \2", option.__class__.__name__)
            self.set_title(i, title)
        return self.options

    def _update_value(self, change: T.Bunch = None):
        value = {}
        for option in self.options:
            if option.value is not None:
                value[option.identifier] = option.value
        self.value = value

    def get(self, key: Union[str, Type[LayoutOptionWidget]]) -> LayoutOptionWidget:
        """Get the `LayoutOptionWidget` instance in for this option group for
        the given key

        :param key: Key to lookup option
        :type key: Union[str, Type[LayoutOptionWidget]]
        :raises KeyError: [description]
        :return: Instance of the associated layout option widget
        :rtype: LayoutOptionWidget
        """
        identifier = key
        try:
            if issubclass(key, LayoutOptionWidget):
                identifier = key.identifier
        except TypeError:
            pass  # okay if key is not a class

        for option in self.options:
            if option.identifier == identifier:
                return option
        raise KeyError(f"`{key}` is not a valid option for this widget")
