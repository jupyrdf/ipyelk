# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W


class ControlOverlay(W.VBox):
    """Simple Container Widget for rendering element specific jupyterlab widgets"""

    # TODO config to specify on which side of selected element's bounding box to
    # render the controls
    # TODO styling for controls

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.children = [W.Button(description="Simple Button")]
