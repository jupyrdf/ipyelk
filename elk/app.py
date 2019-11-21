import ipywidgets as W
import traitlets as T

from typing import Optional, Dict
from .styled_widget import StyledVBox
from .diagram import ElkDiagram


class ElkTransformer(W.Widget):
    value = T.Dict(kw={})

    def to_dict(self):
        return {}

    def refresh(self) -> Dict:
        """Method to update this transform's value"""
        self.value = self.to_dict()
        return self.value


class Elk(StyledVBox):
    transformer = T.Instance(ElkTransformer)
    diagram = T.Instance(ElkDiagram)

    _link: T.dlink = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_link()
        self._update_children()

    @T.default("diagram")
    def _default_diagram(self):
        self.d = ElkDiagram()
        return self.d

    @T.default("transformer")
    def _default_transformer(self):
        return ElkTransformer()

    @T.observe("diagram", "transformer")
    def _update_link(self, change: T.Bunch = None):
        if isinstance(self._link, T.link):
            self._link.unlink()
            self._link = None
        if self.transformer and self.diagram:
            self._link = T.dlink((self.transformer, "value"), (self.diagram, "value"))

    @T.observe("diagram")
    def _update_children(self, change: T.Bunch = None):
        self.children = [self.diagram]

    def refresh(self):
        self.transformer.refresh()
