# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T

from typing import List

from .layout_widgets import LayoutOptionWidget
from ..elk_model import ElkNode, ElkPort


PORT_CONSTRAINT_OPTIONS = {
    "Undefined": "UNDEFINED",
    "Free": "FREE",
    "Fixed Side": "FIXED_SIDE",
    "Fixed Ratio": "FIXED_RATIO",
    "Fixed Position": "FIXED_POS"
}


PORT_SIDE_OPTIONS = {
    "Undefined": "UNDEFINED",
    "North": "NORTH",
    "East": "EAST",
    "South": "SOUTH",
    "West": "WEST",
}


class PortSide(LayoutOptionWidget):
    """The side of a node on which a port is situated. This option must be set if ‘Port Constraints’
    is set to FIXED_SIDE or FIXED_ORDER and no specific positions are given for the ports.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-port-side.html
    """
    identifier = "org.eclipse.elk.port.side"
    applies_to = [ElkPort]
    group = "port"

    value = T.Enum(values=list(PORT_SIDE_OPTIONS.values()), default_value="UNDEFINED")

    def _ui(self)-> List[W.Widget]:
        dropdown = W.Dropdown(options=list(PORT_SIDE_OPTIONS.items()))
        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class PortAnchorOffset(LayoutOptionWidget):
    """The offset to the port position where connections shall be attached.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-port-anchor.html
    """
    identifier = "org.eclipse.elk.port.anchor"
    applies_to = [ElkPort]
    group = "port"

    x = T.Int(default_value=0)
    y = T.Int(default_value=0)
    value = T.Unicode(allow_none=True)

    def _ui(self)-> List[W.Widget]:
        x_slider = W.IntSlider(description="Width")
        y_slider = W.IntSlider(description="Height")

        T.link((self, 'x'), (x_slider, 'value'))
        T.link((self, 'y'), (y_slider, 'value'))
        return [
            x_slider,
            y_slider,
        ]

    @T.observe("x", "y")
    def _update_value(self, change=None):
        self.value = f"({self.x}, {self.y})"


class PortIndex(LayoutOptionWidget):
    """The index of a port in the fixed order around a node. The order is assumed as 
    clockwise, starting with the leftmost port on the top side. This option must be 
    set if ‘Port Constraints’ is set to FIXED_ORDER and no specific positions are 
    given for the ports. Additionally, the option ‘Port Side’ must be defined in this 
    case.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-port-index2.html
    """
    identifier = "org.eclipse.elk.port.index"
    applies_to = [ElkPort]
    group = "port"

    index = T.Int(default_value=0)

    def _ui(self)-> List[W.Widget]:
        index_input = W.IntText(description="Port Index")

        T.link((self, 'index'), (index_input, 'value'))
        return [index_input]

    @T.observe("index")
    def _update_value(self, change=None):
        self.value = f"{self.index}"


class PortBorderOffset(LayoutOptionWidget):
    """The offset of ports on the node border. With a positive offset the port is moved
    outside of the node, while with a negative offset the port is moved towards the
    inside. An offset of 0 means that the port is placed directly on the node border,
    i.e. if the port side is north, the port’s south border touches the nodes’s north
    border; if the port side is east, the port’s west border touches the nodes’s east
    border; if the port side is south, the port’s north border touches the node’s south
    border; if the port side is west, the port’s east border touches the node’s west
    border.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-port-index2.html
    """
    identifier = "org.eclipse.elk.port.borderOffset"
    applies_to = [ElkPort]
    group = "port"

    offset = T.Float(default_value=0)

    def _ui(self)-> List[W.Widget]:
        slider = W.FloatSlider(description="Port BorderOffset", min=-20, max=20, default_value=0)

        T.link((self, 'offset'), (slider, 'value'))
        return [slider]

    @T.observe("offset")
    def _update_value(self, change=None):
        self.value = f"{self.offset}"


class PortSpacing(LayoutOptionWidget):
    """The offset of ports on the node border. With a positive offset the port is moved
    outside of the node, while with a negative offset the port is moved towards the
    inside. An offset of 0 means that the port is placed directly on the node border,
    i.e. if the port side is north, the port’s south border touches the nodes’s north
    border; if the port side is east, the port’s west border touches the nodes’s east
    border; if the port side is south, the port’s north border touches the node’s south
    border; if the port side is west, the port’s east border touches the node’s west
    border.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-port-index2.html
    """
    identifier = "org.eclipse.elk.spacing.portPort"
    applies_to = ["parents", ElkNode]
    group = "spacing"

    spacing = T.Float(default_value=10)

    def _ui(self)-> List[W.Widget]:
        slider = W.FloatSlider(description="Port Spacing", min=0, max=20, default_value=10)

        T.link((self, 'spacing'), (slider, 'value'))
        return [slider]

    @T.observe("offset")
    def _update_value(self, change=None):
        self.value = f"{self.offset}"

class PortConstraints(LayoutOptionWidget):
    """Defines constraints of the position of the ports of a node.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-portconstraints.html
    """
    identifier = "org.eclipse.elk.portConstraints"
    applies_to = [ElkNode]

    value = T.Enum(values=list(PORT_CONSTRAINT_OPTIONS.values()), default_value="UNDEFINED")

    def _ui(self)-> List[W.Widget]:
        dropdown = W.Dropdown(options=[(k,v) for k,v in PORT_CONSTRAINT_OPTIONS.items()])
        T.link((self, "value"), (dropdown, "value"))

        return [dropdown]


class PortLabelPlacement(LayoutOptionWidget):
    """Decides on a placement method for port labels; if empty, the node label’s position is not modified.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-portlabels-placement.html
    """
    identifier = "org.eclipse.elk.portLabels.placement"
    metadata_provider = "org.options.CoreOptions"
    applies_to = [ElkNode]
    group = "portLabels"

    inside = T.Bool(default_value=True)
    next_to_port = T.Bool(default_value=True)
    always_same_side = T.Bool(default_value=True)
    space_efficient = T.Bool(default_value=True)

    value = T.Unicode(allow_none=True)

    def _ui(self)-> List[W.Widget]:
        cb_inside = W.Checkbox(description="Inside")
        cb_next_to_port = W.Checkbox(description="Next to Port if Possible")
        cb_always_same_side = W.Checkbox(description="Always Same Side")
        cb_space_efficient = W.Checkbox(description="Space Efficient")

        T.link((self, "inside"), (cb_inside, "value"))
        T.link((self, "next_to_port"), (cb_next_to_port, "value"))
        T.link((self, "always_same_side"), (cb_always_same_side, "value"))
        T.link((self, "space_efficient"), (cb_space_efficient, "value"))

        return [
            cb_inside,
            cb_next_to_port,
            cb_always_same_side,
            cb_space_efficient,
        ]


    @T.observe("inside", "next_to_port", "always_same_side", "space_efficient")
    def _update_value(self, change=None):
        options = ["INSIDE" if self.inside else "OUTSIDE"]
        if self.next_to_port:
            options.append("NEXT_TO_PORT_IF_POSSIBLE")
        if self.always_same_side:
            options.append("ALWAYS_SAME_SIDE")

        if self.space_efficient:
            options.append("SPACE_EFFICIENT")

        if options:
            self.value = ' '.join(options)
        else:
            self.value = None



class TreatPortLabelsAsGroup(LayoutOptionWidget):
    """If this option is true (default), the labels of a port will be treated as a group 
    when it comes to centering them next to their port. If this option is false, only the 
    first label will be centered next to the port, with the others being placed below. 
    This only applies to labels of eastern and western ports and will have no effect if 
    labels are not placed next to their port.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-portlabels-treatasgroup.html
    """

    identifier = "org.eclipse.elk.portLabels.treatAsGroup"
    metadata_provider = "org.options.CoreOptions"
    applies_to = ElkNode
    group = "portLabels"

    treat_as_group = T.Bool(default_value=True)

    def _ui(self)-> List[W.Widget]:
        cb = W.Checkbox(description="Treat Port Labels as Group")

        T.link((self, "treat_as_group"), (cb, "value"))

        return [cb]

    @T.observe("treat_as_group")
    def _update_value(self, change:T.Bunch=None):
        if self.treat_as_group:
            self.value = "true"
        else:
            self.value = None

        
class AdditionalPortSpace(LayoutOptionWidget):
    """Additional space around the sets of ports on each node side. For each side of a node, 
    this option can reserve additional space before and after the ports on each side. 
    For example, a top spacing of 20 makes sure that the first port on the western and eastern 
    side is 20 units away from the northern border.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-portssurrounding.html
    """

    identifier = "org.eclipse.elk.spacing.portsSurrounding"
    metadata_provider = "org.options.CoreOptions"
    applies_to = "parents"
    group = "spacing"

    space = T.Int(min=0, default_value=0)

    def _ui(self)-> List[W.Widget]:

        slider = W.IntSlider(description="Additional Port Space")
        T.link((self, "space"), (slider, "value"))

        return [slider]

    @T.observe("space")
    def _update_value(self, change:T.Bunch = None):
        self.value = f"{self.space}"

