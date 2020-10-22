"""Set of Widgets to help configure Elk Layout Options
https://www.eclipse.org/elk/reference/options.html
"""
# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from .layout_widgets import LayoutOptionWidget, SpacingOptionWidget, OptionsWidget
from .node_options import NodeLabelPlacement, NodeSizeContraints, NodeSizeMinimum
from .port_options import (
    AdditionalPortSpace, 
    PortAnchorOffset,
    PortBorderOffset, 
    PortConstraints,
    PortIndex,
    PortSide,
    PortLabelPlacement,
    TreatPortLabelsAsGroup,
)
from .edge_options import (
    EdgeLabelPlacement,
    EdgeNodeLayerSpacing,
    EdgeSpacing,
    EdgeThickness,
    EdgeNodeSpacing,
    EdgeLabelSpacing,
)