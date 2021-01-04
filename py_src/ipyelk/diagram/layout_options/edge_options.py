# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import List

import ipywidgets as W
import traitlets as T

from ..elk_model import ElkEdge, ElkLabel
from .selection_widgets import LayoutOptionWidget, SpacingOptionWidget

EDGE_LABEL_OPTIONS = {
    "Center": "CENTER",
    "Head": "HEAD",
    "Tail": "TAIL",
}


EDGE_TYPE_OPTIONS = {
    "None": "NONE",
    "Directed": "DIRECTED",
    "Undirected": "UNDIRECTED",
    "Association": "ASSOCIATION",
    "Generalization": "GENERALIZATION",
    "Dependency": "DEPENDENCY",
}


EDGESIDE_OPTIONS = {
    "Alway Up": "ALWAYS_UP",
    "Always Down": "ALWAYS_DOWN",
    "Direction Down": "DIRECTION_DOWN",
    "Smart Up": "SMART_UP",
    "Smart Down": "SMART_DOWN",
}


EDGE_LABEL_PLACEMENT_STRATEGY = {
    "Median Layer": "MEDIAN_LAYER",
    "Tail Layer": "TAIL_LAYER",
    "Head Layer": "HEAD_LAYER",
    "Space Efficient Layer": "SPACE_EFFICIENT_LAYER",
    "Widest Layer": "WIDEST_LAYER",
    "Center Layer": "CENTER_LAYER",
}


EDGE_ROUTING_OPTIONS = {
    "Undefined": "UNDEFINED",
    "Polyline": "POLYLINE",
    "Orthogonal": "ORTHOGONAL",
    "Splines": "SPLINES",
}

DIRECTION_OPTIONS = {
    "Undefined": "UNDEFINED",
    "Right": "RIGHT",
    "Left": "LEFT",
    "Down": "DOWN",
    "Up": "UP",
}


class InlineEdgeLabels(LayoutOptionWidget):
    """If true, an edge label is placed directly on its edge. May only apply to
    center edge labels. This kind of label placement is only advisable if the
    label’s rendering is such that it is not crossed by its edge and thus stays
    legible.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-edgeLabels-inline.html
    """

    identifier = "org.eclipse.elk.edgeLabels.inline"
    applies_to = ElkLabel

    group = "edgeLabels"

    inline = T.Bool(default_value=False)

    def _ui(self) -> List[W.Widget]:
        cb = W.Checkbox(description="Inline Edge Labels")

        T.link((self, "inline"), (cb, "value"))
        return [cb]

    @T.observe("inline")
    def _update_value(self, change: T.Bunch = None):
        self.value = "true" if self.inline else "false"


class EdgeLabelPlacement(LayoutOptionWidget):
    """Gives a hint on where to put edge labels.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-edgeLabels-placement.html
    """

    identifier = "org.eclipse.elk.edgeLabels.placement"
    applies_to = ElkLabel
    group = "edgeLabels"

    value = T.Enum(values=list(EDGE_LABEL_OPTIONS.values()), default_value="CENTER")

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(
            description="Edge Label Placement", options=list(EDGE_LABEL_OPTIONS.items())
        )

        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class EdgeType(LayoutOptionWidget):
    """The type of an edge. This is usually used for UML class diagrams, where
    associations must be handled differently from generalizations.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-edge-type.html
    """

    identifier = "org.eclipse.elk.edge.type"
    applies_to = [ElkEdge]
    group = "edge"

    value = T.Enum(values=list(EDGE_TYPE_OPTIONS.values()), default_value="NONE")

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(
            description="Edge Type", options=list(EDGE_TYPE_OPTIONS.items())
        )

        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class EdgeThickness(LayoutOptionWidget):
    """The thickness of an edge. This is a hint on the line width used to draw
    an edge, possibly requiring more space to be reserved for it.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-edge-thickness.html
    """

    identifier = "org.eclipse.elk.edge.thickness"
    applies_to = [ElkEdge]
    group = "edge"

    thickness = T.Float(default_value=1, min=0)

    def _ui(self) -> List[W.Widget]:
        slider = W.FloatSlider(description="Edge Thickness", min=0)

        T.link((self, "thickness"), (slider, "value"))

        return [slider]

    @T.observe("thickness")
    def _update_value(self, change: T.Bunch = None):
        self.value = str(self.thickness)


class EdgeSpacing(SpacingOptionWidget):
    """Spacing to be preserved between any two edges. Note that while this can
    somewhat easily be satisfied for the segments of orthogonally drawn edges,
    it is harder for general polylines or splines.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-edgeEdge.html
    """

    identifier = "org.eclipse.elk.edge.edgeEdge"
    applies_to = ["parents"]
    group = "spacing"
    _slider_description: str = "Edge Spacing"


class EdgeNodeSpacing(SpacingOptionWidget):
    """Spacing to be preserved between nodes and edges.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-edgeNode.html
    """

    identifier = "org.eclipse.elk.edge.edgeNode"
    applies_to = ["parents"]
    group = "spacing"
    _slider_description = "Edge Node Spacing"


class EdgeEdgeLayerSpacing(SpacingOptionWidget):
    """Spacing to be preserved between pairs of edges that are routed between
    the same pair of layers. Note that ‘spacing.edgeEdge’ is used for the
    spacing between pairs of edges crossing the same layer.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-spacing-edgeEdgeBetweenLayers.html
    """

    identifier = "org.eclipse.elk.edge.edgeEdgeBetweenLayers"
    applies_to = ["parents"]
    group = "spacing"
    _slider_description = "Edge Edge Between Layer Spacing"


class EdgeNodeLayerSpacing(SpacingOptionWidget):
    """The spacing to be preserved between nodes and edges that are routed next
    to the node’s layer. For the spacing between nodes and edges that cross the
    node’s layer‘spacing.edgeNode’ is used.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-spacing-edgeNodeBetweenLayers.html
    """

    identifier = "org.eclipse.elk.edge.edgeNodeBetweenLayers"
    applies_to = ["parents"]
    group = "spacing"
    _slider_description = "Edge Node Layer Spacing"


class EdgeLabelSpacing(SpacingOptionWidget):
    """The minimal distance to be preserved between a label and the edge it is
     associated with. Note that the placement of a label is influenced by the
     ‘edgelabels.placement’ option.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-edgeLabel.html
    """

    identifier = "org.eclipse.elk.edge.edgeLabel"
    applies_to = ["parents"]
    group = "spacing"
    _slider_description = "Edge Label Spacing"

    spacing = T.Float(default_value=2, min=0)


class EdgeLabelSideSelection(LayoutOptionWidget):
    """Method to decide on edge label sides.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-edgeLabels-sideSelection.html
    """

    identifier = "org.eclipse.elk.layered.edgeLabels.sideSelection"
    applies_to = ["parents"]
    group = "edgeLabels"

    value = T.Enum(values=list(EDGESIDE_OPTIONS.values()), default_value="SMART_DOWN")

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(
            description="Edge Label Side Selection",
            options=list(EDGESIDE_OPTIONS.items()),
        )

        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class EdgeCenterLabelPlacementStrategy(LayoutOptionWidget):
    """Determines in which layer center labels of long edges should be placed.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-edgeLabels-centerLabelPlacementStrategy.html
    """

    identifier = "org.eclipse.elk.layered.edgeLabels.centerLabelPlacementStrategy"
    applies_to = ["parents", ElkLabel]
    group = "edgeLabels"

    value = T.Enum(
        values=list(EDGE_LABEL_PLACEMENT_STRATEGY.values()),
        default_value="MEDIAN_LAYER",
    )

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(
            description="Edge Label Side Selection",
            options=list(EDGE_LABEL_PLACEMENT_STRATEGY.items()),
        )

        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class EadesRepulsion(LayoutOptionWidget):
    """Factor for repulsive forces in Eades’ model.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-force-repulsion.html
    """

    identifier = "org.eclipse.elk.force.repulsion"
    metadata_provider = "options.ForceMetaDataProvider"
    applies_to = ["parents"]
    group = "edgeLabels"

    repulsion = T.Float(default_value=5, min=0.001)

    def _ui(self) -> List[W.Widget]:
        slider = W.FloatSlider(min=0.001)
        T.link((self, "repulsion"), (slider, "value"))

        return [slider]

    @T.observe("repulsion")
    def _update_value(self, change: T.Bunch = None):
        self.value = str(self.repulsion)


class EdgeRouting(LayoutOptionWidget):
    """What kind of edge routing style should be applied for the content of a
    parent node. Algorithms may also set this option to single edges in order to
    mark them as splines. The bend point list of edges with this option set to
    SPLINES must be interpreted as control points for a piecewise cubic spline.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-edgeRouting.html
    """

    identifier = "org.eclipse.elk.edgeRouting"
    metadata_provider = "core.options.CoreOptions"
    applies_to = ["parents"]

    value = T.Enum(
        values=list(EDGE_ROUTING_OPTIONS.values()), default_value="UNDEFINED"
    )

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(
            description="Edge Label Side Selection",
            options=list(EDGE_ROUTING_OPTIONS.items()),
        )

        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class FeedbackEdges(LayoutOptionWidget):
    """Whether feedback edges should be highlighted by routing around the nodes.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-feedbackEdges.html
    """

    identifier = "org.eclipse.elk.layered.feedbackEdges"
    metadata_provider = "options.LayeredMetaDataProvider"
    applies_to = ["parents"]
    reroute = T.Bool(default_value=False)

    def _ui(self) -> List[W.Widget]:

        cb = W.Checkbox()

        T.link((self, "reroute"), (cb, "value"))
        return [cb]

    @T.observe("reroute")
    def _update_value(self, change: T.Bunch = None):
        self.value = "true" if self.reroute else "false"


class MergeEdges(LayoutOptionWidget):
    """Edges that have no ports are merged so they touch the connected nodes at
    the same points. When this option is disabled, one port is created for each
    edge directly connected to a node. When it is enabled, all such incoming
    edges share an input port, and all outgoing edges share an output port.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-mergeEdges.html
    """

    identifier = "org.eclipse.elk.layered.mergeEdges"
    metadata_provider = "options.LayeredMetaDataProvider"
    applies_to = ["parents"]

    merge = T.Bool(default_value=False)

    def _ui(self) -> List[W.Widget]:
        cb = W.Checkbox(description="Merge Edges")

        T.link((self, "merge"), (cb, "value"))
        return [cb]

    @T.observe("merge")
    def _update_value(self, change: T.Bunch = None):
        self.value = "true" if self.merge else "false"


class MergeHierarchyCrossingEdges(LayoutOptionWidget):
    """If hierarchical layout is active, hierarchy-crossing edges use as few
    hierarchical ports as possible. They are broken by the algorithm, with
    hierarchical ports inserted as required. Usually, one such port is created
    for each edge at each hierarchy crossing point. With this option set to
    true, we try to create as few hierarchical ports as possible in the process.
    In particular, all edges that form a hyperedge can share a port.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-layered-mergeHierarchyEdges.html
    """

    identifier = "org.eclipse.elk.layered.mergeHierarchyEdges"
    metadata_provider = "options.LayeredMetaDataProvider"
    applies_to = ["parents"]

    merge = T.Bool(default_value=True)

    def _ui(self) -> List[W.Widget]:
        cb = W.Checkbox(description="Merge Hierarchy Crossing Edges")
        T.link((self, "merge"), (cb, "value"))
        return [cb]

    @T.observe("merge")
    def _update_value(self, change: T.Bunch = None):
        self.value = "true" if self.merge else "false"


class Direction(LayoutOptionWidget):
    """Overall direction of edges: horizontal (right / left) or vertical (down / up).

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-direction.html
    """

    identifier = "org.eclipse.elk.direction"
    metadata_provider = "core.options.CoreOptions"
    applies_to = ["parents"]

    value = T.Enum(values=list(DIRECTION_OPTIONS.values()), default_value="UNDEFINED")

    def _ui(self) -> List[W.Widget]:
        dropdown = W.Dropdown(options=list(DIRECTION_OPTIONS.items()))
        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]
