import ipywidgets as W
import traitlets as T


@W.register
class StyledWidget(W.DOMWidget):
    custom_style = T.Dict()
    _css_html = T.Instance(W.HTML)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_class(self._css_class)

    @property
    def _css_class(self) -> str:
        """CSS Class to namespace custom css classes"""
        return f"morphology-{id(self)}"

    @T.default("_css_html")
    def _default_css_html(self):
        css_widget = W.HTML(value=self.get_css())
        css_widget.layout.display = "None"

        def update_css(*args):
            css_widget.value = self.get_css()

        self.observe(update_css, "custom_style")
        return css_widget

    def css_widget(self):
        """Older method left until refactoring"""
        return self._css_html

    def get_css(self) -> str:
        """Build the custom css to attach to the dom"""
        style = []
        for cls, attrs in self.custom_style.items():
            selector = f".{self._css_class} {cls}"
            css_attributes = (
                "{"
                + "".join([f"{key}: {value};" for key, value in attrs.items()])
                + "}"
            )
            style.append(f"{selector}{css_attributes}")
        return f"<style>{''.join(style)}</style>"

    @property
    def _css_class(self) -> str:
        """CSS Class to namespace custom css classes"""
        return f"styled-widget-{id(self)}"


class StyledVBox(StyledWidget, W.VBox):
    @T.validate("children")
    def _validate_children(self, proposal=T.Bunch):
        value = proposal.value
        if len(value) == 0:
            return value
        elif value[0] is not self._css_html:
            value = [self._css_html] + [v for v in value]
        return value
