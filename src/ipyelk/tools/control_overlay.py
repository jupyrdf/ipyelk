# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W


class ControlOverlay(W.VBox):
    """Simple Container Widget for rendering element specific JupyterLab widgets"""

    # TODO(#210): choose the side of the selection's bounding box that the
    # controls render on, and style the controls

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.children = [W.Button(description="Simple Button")]
