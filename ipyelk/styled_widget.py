# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W
import traitlets as T


@W.register
class StyledWidget(W.Box):
    style = T.Dict()
    _css_widget = T.Instance(W.HTML, kw={"layout": {"display": "None"}})

    def __init__(self, *args, **kwargs):
        """Initialize the widget and add custom styling and css class"""
        super().__init__(*args, **kwargs)
        self._update_style()
        self.add_class(self._css_class)

    @T.validate("children")
    def _valid_children(self, proposal):
        """Ensure incoming children include the css widget for the custom styling"""
        value = proposal["value"]
        if value and self._css_widget not in value:
            value = [self._css_widget] + list(value)
        return value

    @T.observe("style")
    def _update_style(self, change: T.Bunch = None):
        """Build the custom css to attach to the dom"""
        style = []
        for _cls, attrs in self.style.items():
            if "@keyframes" not in _cls:
                selector = f".{self._css_class}{_cls}"
                css_attributes = "".join(
                    [f"{key}: {value};" for key, value in attrs.items()]
                )
            else:
                # process keyframe css
                selector = _cls
                attributes = []
                for key, value in attrs.items():
                    steps = []
                    for stop, frame in value.items():
                        steps.append(f"{stop}:{frame};")
                    attributes.append(f"{key} {{{''.join(steps)}}}")
                css_attributes = "".join(attributes)
            style.append(f"{selector}{{{css_attributes}}}")
        self._css_widget.value = f"<style>{''.join(style)}</style>"

    @property
    def _css_class(self) -> str:
        """CSS Class to namespace custom css classes"""
        return f"styled-widget-{id(self)}"
