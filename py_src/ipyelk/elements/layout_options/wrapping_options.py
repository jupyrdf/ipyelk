# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import List

import ipywidgets as W
import traitlets as T

from .selection_widgets import LayoutOptionWidget, SpacingOptionWidget

WRAPPING_STRATEGY_OPTIONS = {
    "Off": "OFF",
    "Single edge edge": "SINGLE_EDGE",
    "Multi Edge": "MULTI_EDGE",
}


class GraphWrappingStrategy(LayoutOptionWidget):
    """For certain graphs and certain prescribed drawing areas it may be
    desirable to split the laid out graph into chunks that are placed side by
    side. The edges that connect different chunks are ‘wrapped’ around from the
    end of one chunk to the start of the other chunk. The points between the
    chunks are referred to as ‘cuts’.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-wrapping-strategy.html
    """

    identifier = "org.eclipse.elk.layered.wrapping.strategy"
    metadata_provider = "options.LayeredMetaDataProvider"
    applies_to = ["parents"]
    group = "wrapping"

    horizontal = T.Enum(values=["left", "center", "right"], default_value="left")
    value = T.Enum(value=WRAPPING_STRATEGY_OPTIONS.values(), default_value="OFF")

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(options=list(WRAPPING_STRATEGY_OPTIONS.items()))
        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class AdditionalWrappedEdgesSpacing(SpacingOptionWidget):
    """To visually separate edges that are wrapped from regularly routed edges
    an additional spacing value can be specified in form of this layout option.
    The spacing is added to the regular edgeNode spacing.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-wrapping-additionalEdgeSpacing.html
    """

    identifier = "org.eclipse.elk.layered.wrapping.additionalEdgeSpacing"
    metadata_provider = "options.LayeredMetaDataProvider"
    applies_to = ["parents"]
    group = "wrapping"

    spacing = T.Float(default_value=10, min=0)
    dependencies = (
        ("org.eclipse.elk.layered.wrapping.strategy", "SINGLE_EDGE"),
        ("org.eclipse.elk.layered.wrapping.strategy", "MULTI_EDGE"),
    )
    _slider_description = "Additional Wrapped Edges Spacing"


class CorrectionFactorForWrapping(SpacingOptionWidget):
    """At times and for certain types of graphs the executed wrapping may
    produce results that are consistently biased in the same fashion: either
    wrapping to often or to rarely. This factor can be used to correct the bias.
    Internally, it is simply multiplied with the ‘aspect ratio’ layout option.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-wrapping-correctionFactor.html
    """

    identifier = "org.eclipse.elk.layered.wrapping.correctionFactor"
    metadata_provider = "options.LayeredMetaDataProvider"
    applies_to = ["parents"]
    group = "wrapping"
    dependencies = (
        ("org.eclipse.elk.layered.wrapping.strategy", "SINGLE_EDGE"),
        ("org.eclipse.elk.layered.wrapping.strategy", "MULTI_EDGE"),
    )
