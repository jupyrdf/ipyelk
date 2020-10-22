"""Set of Widgets to help configure Elk Layout Options
https://www.eclipse.org/elk/reference/options.html
"""
# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from .edge_options import (
    EdgeLabelPlacement,
    EdgeLabelSpacing,
    EdgeNodeLayerSpacing,
    EdgeNodeSpacing,
    EdgeSpacing,
    EdgeThickness,
)
from .layout_widgets import LayoutOptionWidget, OptionsWidget, SpacingOptionWidget
from .node_options import NodeLabelPlacement, NodeSizeConstraints, NodeSizeMinimum
from .port_options import (
    AdditionalPortSpace,
    PortAnchorOffset,
    PortBorderOffset,
    PortConstraints,
    PortIndex,
    PortLabelPlacement,
    PortSide,
    TreatPortLabelsAsGroup,
)

__all__ = [
    "LayoutOptionWidget",
    "OptionsWidget",
    "SpacingOptionWidget",
    "EdgeLabelPlacement",
    "EdgeLabelSpacing",
    "EdgeNodeLayerSpacing",
    "EdgeNodeSpacing",
    "EdgeSpacing",
    "EdgeThickness",
    "NodeLabelPlacement",
    "NodeSizeConstraints",
    "NodeSizeMinimum",
    "AdditionalPortSpace",
    "PortAnchorOffset",
    "PortBorderOffset",
    "PortConstraints",
    "PortIndex",
    "PortLabelPlacement",
    "PortSide",
    "TreatPortLabelsAsGroup",
]
