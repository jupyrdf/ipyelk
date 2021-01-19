# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import field
from typing import ClassVar, Dict, Type

from ...diagram import layout_options as opt
from ...diagram.symbol import Def
from ..elements import Edge, Partition, Record, element
from ..shapes import connectors

content_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="left", vertical="center")]
).value

top_center_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="top")]
).value

center_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="center")]
).value

bullet_opts = opt.OptionsWidget(
    options=[
        opt.LabelSpacing(spacing=4),
    ]
).value

compart_opts = opt.OptionsWidget(
    options=[
        opt.NodeSizeConstraints(),
    ]
).value


@element
class Block(Record):
    pass


@element
class Composition(Edge):
    shape_start: ClassVar[str] = "composition"


@element
class Aggregation(Edge):
    shape_start: ClassVar[str] = "aggregation"


@element
class Containment(Edge):
    shape_start: ClassVar[str] = "containment"


@element
class DirectedAssociation(Edge):
    shape_end: ClassVar[str] = "directed_association"


@element
class Association(Edge):
    pass


@element
class Generalization(Edge):
    shape_start: ClassVar[str] = "generalization"


@element
class BlockDiagram(Partition):
    # TODO flesh out ideas of encapsulating diagram defs / styles / elements
    defs: ClassVar[Dict[str, Def]] = {
        "composition": connectors.Rhomb(r=4),
        "aggregation": connectors.Rhomb(r=4),
        "containment": connectors.Containment(r=4),
        "directed_association": connectors.StraightArrow(r=4),
        "generalization": connectors.StraightArrow(r=4, closed=True),
    }
    style: ClassVar[Dict[str, Def]] = {
        " .elklabel.compartment_title_1": {
            "font-weight": "bold",
        },
        " .elklabel.heading, .elklabel.compartment_title_2": {
            "font-style": "italic",
        },
        " .arrow.inheritance": {
            "fill": "none",
        },
        " .arrow.containment": {
            "fill": "none",
        },
        " .arrow.aggregation": {
            "fill": "none",
        },
        " .arrow.directed_association": {
            "fill": "none",
        },
        " .internal>.elknode": {
            "stroke": "transparent",
            "fill": "transparent",
        },
    }
    default_edge: Type[Edge] = field(default=Association)
