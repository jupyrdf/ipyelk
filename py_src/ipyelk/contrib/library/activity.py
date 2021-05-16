# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict, Type

from pydantic import Field

from ...elements import (
    Edge,
    EdgeProperties,
    Label,
    Node,
    NodeProperties,
    Partition,
    Port,
    Symbol,
    SymbolSpec,
)
from ...elements import layout_options as opt
from ...elements import shapes
from ..molds import connectors, structures

center_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="center")]
).value

heading_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="left", vertical="top")]
).value


node_opts = opt.OptionsWidget(options=[opt.NodeSizeConstraints()]).value

small_port_shape = shapes.PortShape(width=0, height=0)


# symbols
arrow_head = connectors.StraightArrow("arrow", r=4)
init_state = Symbol(
    identifier="initial-state",
    element=Node(properties=NodeProperties(shape=shapes.Circle(radius=6))),
    width=12,
    height=12,
)
exit_state = Symbol(
    identifier="exit-state",
    element=structures.XCircle(radius=6),
    width=12,
    height=12,
)
final_state = Symbol(
    identifier="final-state",
    element=structures.DoubleCircle(radius=6),
    width=12,
    height=12,
)


class Activity(Node):
    properties: NodeProperties = NodeProperties(shape=shapes.Ellipse())

    @classmethod
    def make(cls, text, container=False):
        if container:
            mark = cls(
                labels=[
                    Label(text=text, layoutOptions=heading_label_opts),
                ],
                layoutOptions=node_opts,
                properties=NodeProperties(
                    shape=shapes.Rect(), cssClasses="activity-container"
                ),
            )
            return mark

        return cls(
            labels=[
                Label(text=text, layoutOptions=center_label_opts),
            ],
            layoutOptions=node_opts,
        )


class Merge(Node):
    properties: NodeProperties = NodeProperties(
        cssClasses="activity-filled", shape=shapes.Rect(width=50, height=10)
    )


class Decision(Node):
    properties: NodeProperties = NodeProperties(
        shape=shapes.Diamond(width=20, height=20)
    )

    def __init__(self, **data):
        super().__init__(**data)

        def port_opts(side):
            return opt.OptionsWidget(options=[opt.PortSide(value=side)]).value

        self.add_port(
            key="input",
            port=Port(
                properties={"shape": small_port_shape}, layoutOptions=port_opts("NORTH")
            ),
        )
        self.add_port(
            key="true",
            port=Port(
                properties={"shape": small_port_shape},
                labels=[Label(text="true")],
                layoutOptions=port_opts("WEST"),
            ),
        )
        self.add_port(
            key="false",
            port=Port(
                properties={"shape": small_port_shape},
                labels=[Label(text="false")],
                layoutOptions=port_opts("EAST"),
            ),
        )

        self.layoutOptions[opt.PortConstraints.identifier] = opt.PortConstraints(
            value="FIXED_SIDE"
        ).value


class Join(Node):
    properties: NodeProperties = NodeProperties(
        cssClasses="activity-filled", shape=shapes.Rect(width=50, height=10)
    )


class StartActivity(Node):
    properties: NodeProperties = NodeProperties(
        shape=shapes.Use(use=init_state.identifier, width=12, height=12)
    )


class EndActivity(Node):
    properties: NodeProperties = NodeProperties(
        shape=shapes.Use(use=final_state.identifier, width=12, height=12)
    )


class SimpleArrow(Edge):
    properties: EdgeProperties = EdgeProperties(shape={"end": arrow_head.identifier})


class ActivityDiagram(Partition):
    # TODO flesh out ideas of encapsulating diagram defs / styles / elements
    symbols: SymbolSpec = Field(
        SymbolSpec().add(
            init_state,
            exit_state,
            final_state,
            arrow_head,
        ),
        exclude=True,
    )

    style: Dict[str, Dict] = Field(
        {
            " .final-state .inner-circle": {
                "fill": "var(--jp-elk-node-stroke)",
            },
            " .activity-filled .elknode": {
                "fill": "var(--jp-elk-node-stroke)",
            },
            " .activity-container > .elknode": {
                "rx": "var(--jp-code-font-size)",
            },
        },
        exclude=True,
    )
    default_edge: Type[Edge] = Field(default=SimpleArrow)
