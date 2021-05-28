"""Widget for exporting a diagram. Currently supports SVG.
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from .diagram import Diagram
from .viewer import Viewer


class Exporter(W.Widget):
    """exports elk diagrams"""

    _model_name = T.Unicode("ELKExporterModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKExporterView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    viewer: Viewer = T.Instance(Viewer, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )
    value: str = T.Unicode(allow_none=True).tag(sync=True)
    enabled: bool = T.Bool(default_value=True).tag(sync=True)
    extra_css: str = T.Unicode(default_value="").tag(sync=True)
    padding: float = T.Float(20).tag(sync=True)
    diagram: Diagram = T.Instance(Diagram, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )
    strip_ids = T.Bool(default_value=True).tag(sync=True)
    add_xml_header = T.Bool(default_value=True).tag(sync=True)

    @T.observe("diagram")
    def _set_viewer(self, change):
        if change and isinstance(change.new, Diagram):
            self.viewer = change.new.view
