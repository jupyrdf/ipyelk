# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict

import traitlets as T

from ..diagram.elk_model import ElkEdge, ElkLabel, ElkNode, ElkPort, ElkRoot
from ..diagram.layout_options import LayoutOptionWidget, OptionsWidget


# TODO Layout dictionary widget needs to be reimplemented to allow more flexible
# programatic setting of layout options
class XELKTypedLayout(OptionsWidget):

    selected = T.Any(
        default_value=ElkRoot
    )  # placeholder trait while playing with patterns
    value = (
        T.Dict()
    )  # TODO get some typing around the dictionary e.g. Dict[Hashable, NEWDATACLASS]
    _type_map = {
        "Parents": "parents",
        "Node": ElkNode,
        "Label": ElkLabel,
        "Edge": ElkEdge,
        "Port": ElkPort,
    }

    def __init__(self, *args, **kwargs):

        groups = []

        for title, element_type in self._type_map.items():
            group = []
            for identifier, cls_widget in self._collect_type_options().items():
                if cls_widget.matches(element_type):
                    group.append(cls_widget())

            option_group = OptionsWidget(options=group)
            option_group.identifier = element_type
            option_group.title = title

            option_group.observe(self._update_value, "value")

            groups.append(option_group)
        self.options = groups

        super().__init__(*args, **kwargs)
        self.children = self._ui()

    def _collect_type_options(self):
        return type_options(LayoutOptionWidget)

    def _update_value(self, change: T.Bunch = None):
        if change and change.new:
            self.value[self.selected][change.owner.identifier] = change.new
        else:
            self.value[self.selected] = {
                opt.identifier: opt.value for opt in self.options
            }
        self._notify_trait("value", {}, self.value)

    def get(self, element_type) -> OptionsWidget:
        """Get the `OptionsWidget` for the given element_type according to the
        current active selection
        """
        for option in self.options:
            if option.identifier == element_type:
                return option
        raise KeyError(f"`{element_type}` is not a valid element for this widget")


def type_options(cls, registry=None) -> Dict:
    if registry is None:
        registry = {}
    for sub_cls in cls.__subclasses__():
        if sub_cls.identifier is None:
            type_options(sub_cls, registry)
            continue
        if sub_cls.identifier in registry:
            existing = registry[sub_cls.identifier]
            raise ValueError(f"Duplicated Identifiers for `{sub_cls}` and `{existing}`")
        registry[sub_cls.identifier] = sub_cls
    return registry
