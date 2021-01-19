# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass
from typing import List

import ipywidgets as W
import traitlets as T

from .selection_widgets import LayoutOptionWidget


@dataclass
class Algorithm:
    identifier: str
    metadata_provider: str
    title: str


class Draw2DLayout(Algorithm):
    """
    https://www.eclipse.org/elk/reference/algorithms/org-eclipse-elk-conn-gmf-layouter-Draw2D.html
    """

    identifier = "org.eclipse.elk.conn.gmf.layouter.Draw2D"
    metadata_provider = "GmfMetaDataProvider"
    title = "Draw2D Layout"


class ELKBox(Algorithm):
    """
    https://www.eclipse.org/elk/reference/algorithms/org-eclipse-elk-box.html
    """

    identifier = "org.eclipse.elk.box"
    metadata_provider = "core.options.CoreOptions"
    title = "ELK BoX"


class ELKRadial(Algorithm):
    """
    https://www.eclipse.org/elk/reference/algorithms/org-eclipse-elk-radial.html
    """

    identifier = "org.eclipse.elk.radial"
    metadata_provider = "options.RadialMetaDataProvider"
    title = "ELK Radial"


class ELKLayered(Algorithm):
    """
    https://www.eclipse.org/elk/reference/algorithms/org-eclipse-elk-layered.html
    """

    identifier = "org.eclipse.elk.layered"
    metadata_provider = "options.LayeredMetaDataProvider"
    title = "ELK Layered"


class ELKRectanglePacking(Algorithm):
    """
    https://www.eclipse.org/elk/reference/algorithms/org-eclipse-elk-rectpacking.html
    """

    identifier = "org.eclipse.elk.rectpacking"
    metadata_provider = "options.RectPackingMetaDataProvider"
    title = "Elk Rectangle Packing"


ALGORITHM_OPTIONS = {_cls.identifier: _cls for _cls in Algorithm.__subclasses__()}


class LayoutAlgorithm(LayoutOptionWidget):
    """Select a specific layout algorithm.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-algorithm.html
    """

    identifier = "org.eclipse.elk.algorithm"

    value = T.Enum(
        values=list(ALGORITHM_OPTIONS.keys()), default_value=ELKLayered.identifier
    )
    metadata_provider = T.Unicode()
    applies_to = ["parents"]

    def _ui(self) -> List[W.Widget]:
        options = [
            (_cls.title, identifier) for (identifier, _cls) in ALGORITHM_OPTIONS.items()
        ]
        dropdown = W.Dropdown(description="Layout Algorithm", options=options)

        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]

    @T.default("metadata_provider")
    def _default_metadata_provider(self):
        """Default value for the current metadata provider"""
        return self._update_metadata_provider()

    @T.observe("value")
    def _update_metadata_provider(self, change: T.Bunch = None):
        """Change Handler to update the metadata provider based on current
        selected algorithm
        """

        provider = ALGORITHM_OPTIONS[self.value].metadata_provider
        self.metadata_provider = provider
        return provider
