# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import List

import ipywidgets as W
import traitlets as T

from ..elk_model import ElkLabel, ElkNode
from .layout_widgets import LayoutOptionWidget

NODESIZE_OPTIONS_OPTIONS = {
    "default_minimum_size": "DEFAULT_MINIMUM_SIZE",
    "minimum_size_accounts_for_padding": "MINIMUM_SIZE_ACCOUNTS_FOR_PADDING",
    "compute_padding": "COMPUTE_PADDING",
    "outside_node_labels_overhang": "OUTSIDE_NODE_LABELS_OVERHANG",
    "ports_overhang": "PORTS_OVERHANG",
    "uniform_port_spacing": "UNIFORM_PORT_SPACING",
    "force_tabular_node_labels": "FORCE_TABULAR_NODE_LABELS",
    "asymmetrical": "ASYMMETRICAL",
}


class NodeSizeConstraints(LayoutOptionWidget):
    """What should be taken into account when calculating a node’s size. Empty
    size constraints specify that a node’s size is already fixed and should not
    be changed.
    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-nodesize-constraints.html

    Size constraints basically restrict the freedom a layout algorithm has in
    resizing a node subject to its node labels, ports, and port labels. The
    different values have the following meanings:
        * NODE_LABELS - The node can be made large enough to place all node labels
        without violating spacing constraints.
        * PORTS - The node can be made large enough to place all of its ports
          without violating spacing constraints.
        * PORT_LABELS - If Ports is active, not only the ports themselves are
        considered, but also their labels.
        * MINIMUM_SIZE - The node must meet a given minimum size specified through
        the Node Size Minimum option.
    """

    identifier = "org.eclipse.elk.nodeSize.constraints"
    metadata_provider = "core.options.CoreOptions"
    applies_to = [ElkNode]
    group = "nodeSize"

    node_labels = T.Bool(default_value=True)
    ports = T.Bool(default_value=True)
    port_labels = T.Bool(default_value=True)
    minimum_size = T.Bool(default_value=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_value()

    def _ui(self) -> List[W.Widget]:
        cb_node_labels = W.Checkbox(description="Node Labels")
        cb_ports = W.Checkbox(description="Port")
        cb_port_labels = W.Checkbox(description="Port Labels")
        cb_minimum_size = W.Checkbox(description="Minimum Size")

        T.link((self, "node_labels"), (cb_node_labels, "value"))
        T.link((self, "ports"), (cb_ports, "value"))
        T.link((self, "port_labels"), (cb_port_labels, "value"))
        T.link((self, "minimum_size"), (cb_minimum_size, "value"))

        return [
            cb_node_labels,
            cb_ports,
            cb_port_labels,
            cb_minimum_size,
        ]

    @T.observe("node_labels", "ports", "port_labels", "minimum_size")
    def _update_value(self, change=None):
        value = []
        if self.node_labels:
            value.append("NODE_LABELS")
        if self.ports:
            value.append("PORTS")
        if self.port_labels:
            value.append("PORT_LABELS")
        if self.minimum_size:
            value.append("MINIMUM_SIZE")
        if value:
            self.value = " ".join(value)
        else:
            self.value = None


class NodeSizeMinimum(LayoutOptionWidget):
    """The minimal size to which a node can be reduced.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-nodesize-minimum.html
    """

    identifier = "org.eclipse.elk.nodeSize.minimum"
    metadata_provider = "core.options.CoreOptions"
    applies_to = [ElkNode]
    group = "nodeSize"

    width = T.Int(default_value=10)
    height = T.Int(default_value=10)

    def _ui(self) -> List[W.Widget]:
        width_slider = W.IntSlider(description="Width")
        height_slider = W.IntSlider(description="Height")

        T.link((self, "width"), (width_slider, "value"))
        T.link((self, "height"), (height_slider, "value"))
        return [
            width_slider,
            height_slider,
        ]

    @T.observe("width", "height")
    def _update_value(self, change=None):
        self.value = f"({self.width}, {self.height})"


class NodeSizeOptions(LayoutOptionWidget):
    """Options modifying the behavior of the size constraints set on a node.
    Each member of the set specifies something that should be taken into account
    when calculating node sizes. The empty set corresponds to no further
    modifications.

    Additional Documentation:
        * DEFAULT_MINIMUM_SIZE - Uses a default minimum size if none is
        specified and size constraints include MINIMUM_SIZE.
        * MINIMUM_SIZE_ACCOUNTS_FOR_PADDING - If this option is set and paddings
        are computed by the algorithm, the minimum size plus the computed
        padding are a lower bound on the node size. If this option is not set,
        the minimum size will be applied to the node’s whole size regardless of
        any computed padding. Note that, depending on the algorithm, this option
        may only apply to non-hierarchical nodes. This option only makes sense
        if size constraints include MINIMUM_SIZE.
        * COMPUTE_PADDING - With this option set, the padding of nodes will be
        computed and returned as part of the algorithm’s result. If port labels
        or node labels are placed, they may influence the size of the padding.
        Note that, depending on the algorithm, this option may only apply to
        non-hierarchical nodes. This option is independent of the size
        constraint set on a node.
        * OUTSIDE_NODE_LABELS_OVERHANG - If node labels influence the node size,
        but outside node labels are allowed to overhang, only inside node labels
        actually influence node size.
        * PORTS_OVERHANG - By default, ports only use the space available to
        them, even if that means violating port spacing settings. If this option
        is active, port spacings are adhered to, even if that means ports extend
        beyond node boundaries.
        * UNIFORM_PORT_SPACING - If port labels are taken into consideration,
        differently sized labels can result in a different amount of space
        between different pairs of ports. This option causes all ports to be
        evenly spaced by enlarging the space between every pair of ports to the
        larges amount of space between any pair of ports.
        * FORCE_TABULAR_NODE_LABELS - By default, inside node labels will be
        laid out in three rows of three cells, with no relation between the
        width of cells in different rows. If this option is enabled, the cells
        will be treated as cells of a table, with equal columns across all rows.
        This usually results in larger nodes.
        * ASYMMETRICAL - If this option is set, the node sizing and label
        placement code will not make an attempt to achieve a symmetrical layout.
        With this option inactive, for example, the space reserved for left
        inside port labels will be the same as for right inside port labels,
        which would not be the case otherwise. Deactivating this option will
        also ensure that center node labels will actually be placed in the
        center.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-nodesize-options.html
    """

    identifier = "org.eclipse.elk.nodeSize.options"
    metadata_provider = "core.options.CoreOptions"
    applies_to = [ElkNode]
    group = "nodeSize"

    default_minimum_size = T.Bool(default_value=True)
    minimum_size_accounts_for_padding = T.Bool()
    compute_padding = T.Bool()
    outside_node_labels_overhang = T.Bool()
    ports_overhang = T.Bool()
    uniform_port_spacing = T.Bool()
    force_tabular_node_labels = T.Bool()
    asymmetrical = T.Bool()

    def _ui(self) -> List[W.Widget]:
        checkboxes = []
        for attr, value in NODESIZE_OPTIONS_OPTIONS.items():
            cb = W.Checkbox(description=attr.replace("_", " ").title())
            T.link((self, attr), (cb, "value"))
            checkboxes.append(cb)

        return checkboxes

    @T.observe(
        "default_minimum_size",
        "minimum_size_accounts_for_padding",
        "compute_padding",
        "outside_node_labels_overhang",
        "ports_overhang",
        "uniform_port_spacing",
        "force_tabular_node_labels",
        "asymmetrical",
    )
    def _update_value(self, change: T.Bunch = None):
        options = []
        for attr, option in NODESIZE_OPTIONS_OPTIONS.keys():
            value = getattr(self, attr)
            if value is True:
                options.append(option)
        self.value = " ".join(options)


class NodeLabelPlacement(LayoutOptionWidget):
    """Hints for where node labels are to be placed; if empty, the node label’s
    position is not modified.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-nodelabels-placement.html
    """

    identifier = "org.eclipse.elk.nodeLabels.placement"
    metadata_provider = "core.options.CoreOptions"
    applies_to = [ElkNode, ElkLabel]
    group = "nodeLabels"

    horizontal = T.Enum(values=["left", "center", "right"], default_value="left")
    h_priority = T.Bool(allow_none=True)
    vertical = T.Enum(values=["top", "center", "bottom"], default_value="top")
    inside = T.Enum(values=["inside", "outside"], default_value="inside")

    def _ui(self) -> List[W.Widget]:
        horizontal_options = W.RadioButtons(
            description="Horizontal",
            options=(
                ("Left", "left"),
                ("Center", "center"),
                ("Right", "right"),
            ),
        )
        vertical_options = W.RadioButtons(
            description="Vertical",
            options=(
                ("Top", "top"),
                ("Center", "center"),
                ("Bottom", "bottom"),
            ),
        )
        inside_options = W.Checkbox(description="Inside")
        horizontal_priority_options = W.Checkbox(description="Horizontal Priority")

        T.link((self, "horizontal"), (horizontal_options, "value"))
        T.link((self, "vertical"), (vertical_options, "value"))
        T.link((self, "h_priority"), (horizontal_priority_options, "value"))

        def _handle_inside_option_change(change):
            self.inside = "inside" if inside_options.value is True else "outside"

        def _update_inside_option(change=None):
            inside_options.value = self.inside == "inside"

        inside_options.observe(_handle_inside_option_change, "value")
        self.observe(_update_inside_option, "inside")
        _update_inside_option()

        return [
            horizontal_options,
            vertical_options,
            W.VBox([inside_options, horizontal_priority_options]),
        ]

    @T.observe("horizontal", "vertical", "inside", "h_priority")
    def _update_value(self, change=None):
        options = []
        if self.horizontal:
            options.append(f"H_{self.horizontal.upper()}")
        if self.vertical:
            options.append(f"V_{self.vertical.upper()}")

        is_centered = self.horizontal == "center" and self.vertical == "center"
        inside = "inside" if is_centered else self.inside
        if inside:
            options.append(inside.upper())
        if self.h_priority:
            options.append("H_PRIORITY")
        if options:
            self.value = " ".join(options)
        else:
            self.value = None


class ActivateInsideSelfLoops(LayoutOptionWidget):
    """Whether this node allows to route self loops inside of it instead of
    around it. If set to true, this will make the node a compound node if it
    isn’t already, and will require the layout algorithm to support compound
    nodes with hierarchical ports.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-insideselfloops-activate.html
    """

    identifier = "org.eclipse.elk.insideSelfLoops.activate"
    metadata_provider = "core.options.CoreOptions"
    applies_to = [ElkNode]
    group = "insideSelfLoops"

    activate = T.Bool(default_value=False)

    def _ui(self) -> List[W.Widget]:
        cb = W.Checkbox(description="Activate Inside Self Loops")
        T.link((self, "activate"), (cb, "value"))

        return [cb]

    @T.observe("activate")
    def _update_value(self, change: T.Bunch = None):
        self.value = "true" if self.activate else "false"
