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
    MergeEdges,
)
from .layout import LayoutAlgorithm
from .node_options import (
    ActivateInsideSelfLoops,
    HierarchyHandling,
    NodeLabelPlacement,
    NodeSizeConstraints,
    NodeSizeMinimum,
)
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
from .selection_widgets import LayoutOptionWidget, OptionsWidget, SpacingOptionWidget

__all__ = [
    "ActivateInsideSelfLoops",
    "AdditionalPortSpace",
    "EdgeLabelPlacement",
    "EdgeLabelSpacing",
    "EdgeNodeLayerSpacing",
    "EdgeNodeSpacing",
    "EdgeSpacing",
    "EdgeThickness",
    "HierarchyHandling",
    "LayoutAlgorithm",
    "LayoutOptionWidget",
    "MergeEdges",
    "NodeLabelPlacement",
    "NodeSizeConstraints",
    "NodeSizeMinimum",
    "OptionsWidget",
    "PortAnchorOffset",
    "PortBorderOffset",
    "PortConstraints",
    "PortIndex",
    "PortLabelPlacement",
    "PortSide",
    "SpacingOptionWidget",
    "TreatPortLabelsAsGroup",
]
