# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W
import traitlets as T


@W.register
class StyledWidget(W.Box):
    style = T.Dict(kw={})
    raw_css = T.Tuple().tag(sync=True)
    namespaced_css = T.Unicode().tag(sync=True)
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
        raw_css = []
        for _cls, attrs in self.style.items():
            if "@keyframes" not in _cls:
                selector = f".{self._css_class}{_cls}"
                css_attributes = "\n".join(
                    [f"{key}: {value};" for key, value in attrs.items()]
                )
                raw_css += [f"{_cls}{{ {css_attributes} }}"]
            else:
                # process keyframe css
                selector = _cls
                attributes = []
                for key, value in attrs.items():
                    steps = []
                    for stop, frame in value.items():
                        steps.append(f"{stop}:{frame};")
                    attributes.append(f"{key} {{{''.join(steps)}}}")
                css_attributes = "\n".join(attributes)
            style.append(f"{selector}{{{css_attributes}}}")
        self.namespaced_css = "".join(style)
        self.raw_css = raw_css
        self._css_widget.value = f"<style>{self.namespaced_css}</style>"

    @property
    def _css_class(self) -> str:
        """CSS Class to namespace custom css classes"""
        return f"styled-widget-{id(self)}"
