"""Widget for exporting an Elk diagram. Currently supports SVG.
"""
# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from .elk_widget import ElkDiagram


class ElkExporter(W.Widget):
    """ exports elk diagrams """

    _model_name = T.Unicode("ELKExporterModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKExporterView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    diagram: ElkDiagram = T.Instance(ElkDiagram, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )
    value: str = T.Unicode(allow_none=True).tag(sync=True)
    format: str = T.Unicode(default_value="svg").tag(sync=True)
    enabled: bool = T.Bool(default=True).tag(sync=True)
    extra_css: str = T.Unicode(default_value="").tag(sync=True)
    padding: float = T.Float(20).tag(sync=True)

    @T.observe("diagram")
    def _on_diagram(self, change: T.Bunch) -> None:
        self._unobserve_diagram(change.old)
        self._observe_diagram(change.new)

    def _unobserve_diagram(self, diagram: ElkDiagram) -> None:
        if not diagram:
            return

    def _observe_diagram(self, diagram: ElkDiagram) -> None:
        if not diagram:
            return
