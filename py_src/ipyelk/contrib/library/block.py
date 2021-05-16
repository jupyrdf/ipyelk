# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict, Type

from pydantic import Field

from ...elements import Edge, EdgeProperties, Partition, Record, SymbolSpec
from ...elements import layout_options as opt
from ...elements import merge_excluded
from ..molds import connectors

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


class Block(Record):
    pass


class Composition(Edge):
    properties: EdgeProperties = EdgeProperties(shape={"start": "composition"})


class Aggregation(Edge):
    properties: EdgeProperties = EdgeProperties(shape={"start": "aggregation"})


class Containment(Edge):
    properties: EdgeProperties = EdgeProperties(shape={"start": "containment"})


class DirectedAssociation(Edge):
    properties: EdgeProperties = EdgeProperties(shape={"end": "directed_association"})


class Association(Edge):
    pass


class Generalization(Edge):
    properties: EdgeProperties = EdgeProperties(shape={"start": "generalization"})


class BlockDiagram(Partition):
    # TODO flesh out ideas of encapsulating diagram defs / styles / elements
    class Config:
        copy_on_model_validation = False
        excluded = merge_excluded(Partition, "symbols", "style")

    symbols: SymbolSpec = SymbolSpec().add(
        connectors.Rhomb(identifier="composition", r=4),
        connectors.Rhomb(identifier="aggregation", r=4),
        connectors.Containment(identifier="containment", r=4),
        connectors.StraightArrow(identifier="directed_association", r=4),
        connectors.StraightArrow(identifier="generalization", r=4, closed=True),
    )

    style: Dict[str, Dict] = {
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
    default_edge: Type[Edge] = Field(default=Association)
