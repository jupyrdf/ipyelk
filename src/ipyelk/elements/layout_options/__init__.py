"""set of Widgets to help configure Elk Layout Options
https://www.eclipse.org/elk/reference/options.html
"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from ...exceptions import DeprecatedImportError
from .edge_options import (
    Direction,
    EadesRepulsion,
    EdgeCenterLabelPlacementStrategy,
    EdgeEdgeLayerSpacing,
    EdgeLabelPlacement,
    EdgeLabelSideSelection,
    EdgeLabelSpacing,
    EdgeNodeLayerSpacing,
    EdgeNodeSpacing,
    EdgeRouting,
    EdgeSpacing,
    EdgeThickness,
    EdgeType,
    FeedbackEdges,
    MergeEdges,
    MergeHierarchyCrossingEdges,
)
from .layout import _REMOVED, ELKRectanglePacking, LayoutAlgorithm
from .node_options import (
    ActivateInsideSelfLoops,
    AspectRatio,
    ConsiderModelOrder,
    ContentAlignment,
    ExpandNodes,
    HierarchyHandling,
    NodeLabelPlacement,
    NodeSizeConstraints,
    NodeSizeMinimum,
    NodeSizeOptions,
    Padding,
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
from .spacing_options import (
    CommentCommentSpacing,
    CommentNodeSpacing,
    ComponentsSpacing,
    LabelNodeSpacing,
    LabelSpacing,
    NodeSpacing,
    SeparateConnectedComponents,
)


def __getattr__(name: str) -> object:
    if name in _REMOVED:
        raise DeprecatedImportError(_REMOVED[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ActivateInsideSelfLoops",
    "AdditionalPortSpace",
    "AspectRatio",
    "CommentCommentSpacing",
    "CommentNodeSpacing",
    "ComponentsSpacing",
    "ConsiderModelOrder",
    "ContentAlignment",
    "Direction",
    "EadesRepulsion",
    "EdgeCenterLabelPlacementStrategy",
    "EdgeEdgeLayerSpacing",
    "EdgeLabelPlacement",
    "EdgeLabelSideSelection",
    "EdgeLabelSpacing",
    "EdgeNodeLayerSpacing",
    "EdgeNodeSpacing",
    "EdgeRouting",
    "EdgeSpacing",
    "EdgeThickness",
    "EdgeType",
    "ELKRectanglePacking",
    "ExpandNodes",
    "FeedbackEdges",
    "HierarchyHandling",
    "LabelNodeSpacing",
    "LabelSpacing",
    "LayoutAlgorithm",
    "LayoutOptionWidget",
    "MergeEdges",
    "MergeHierarchyCrossingEdges",
    "NodeLabelPlacement",
    "NodeSizeConstraints",
    "NodeSizeMinimum",
    "NodeSizeOptions",
    "NodeSpacing",
    "OptionsWidget",
    "Padding",
    "PortAnchorOffset",
    "PortBorderOffset",
    "PortConstraints",
    "PortIndex",
    "PortLabelPlacement",
    "PortSide",
    "SeparateConnectedComponents",
    "SpacingOptionWidget",
    "TreatPortLabelsAsGroup",
]
