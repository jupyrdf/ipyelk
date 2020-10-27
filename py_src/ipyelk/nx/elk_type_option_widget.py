# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T

from ipyelk.diagram.elk_model import ElkEdge, ElkLabel, ElkNode, ElkPort

from ..diagram.layout_options import LayoutOptionWidget, OptionsWidget


class XELKTypedLayout(OptionsWidget):

    selected = T.Any(allow_none=True)  # placeholder trait while playing with patterns
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
        self.children = self._ui()
        super().__init__(*args, **kwargs)

    def _collect_type_options(self):
        registry = {}
        for _cls in LayoutOptionWidget.__subclasses__():
            if _cls.identifier is None:
                continue
            if _cls.identifier in registry:
                existing = registry[_cls.identifier]
                raise ValueError(
                    f"Duplicated Identifiers for `{_cls}` and `{existing}`"
                )
            registry[_cls.identifier] = _cls
        return registry

    def _update_value(self, change: T.Bunch = None):
        if change and change.new:
            self.value[self.selected][change.owner.identifier] = change.new
        else:
            self.value[self.selected] = {
                opt.identifier: opt.value for opt in self.options
            }
        self._notify_trait("value", {}, self.value)
