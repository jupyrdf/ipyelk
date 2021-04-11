# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import ClassVar, Dict, Type

from pydantic import Field

from ...diagram import layout_options as opt
from ...diagram.symbol import Def, Symbol, symbols
from ...elements import Edge, Label, Node, Partition, Port
from ..shapes import connectors, shapes

center_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="center")]
).value

heading_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="left", vertical="top")]
).value


node_opts = opt.OptionsWidget(options=[opt.NodeSizeConstraints()]).value

small_port_shape = symbols.Rect(width=0, height=0)


class Activity(Node):
    shape: Symbol = symbols.Ellipse()

    @classmethod
    def make(cls, text, container=False):
        if container:
            mark = cls(
                labels=[
                    Label(text=text, layoutOptions=heading_label_opts),
                ],
                layoutOptions=node_opts,
                properties={"cssClasses": "activity-container"},
            )
            mark.shape = None
            return mark

        return cls(
            labels=[
                Label(text=text, layoutOptions=center_label_opts),
            ],
            layoutOptions=node_opts,
        )


class Merge(Node):
    shape: Symbol = symbols.Rect(width=50, height=10)
    _css_classes = ["activity-filled"]


class Decision(Node):
    shape: Symbol = symbols.Diamond(width=20, height=20)

    def __init__(self, **data):
        super().__init__(**data)

        def port_opts(side):
            return opt.OptionsWidget(options=[opt.PortSide(value=side)]).value

        self.add_port(
            key="input",
            port=Port(shape=small_port_shape, layoutOptions=port_opts("NORTH")),
        )
        self.add_port(
            key="true",
            port=Port(
                shape=small_port_shape,
                labels=[Label(text="true")],
                layoutOptions=port_opts("WEST"),
            ),
        )
        self.add_port(
            key="false",
            port=Port(
                shape=small_port_shape,
                labels=[Label(text="false")],
                layoutOptions=port_opts("EAST"),
            ),
        )

        self.layoutOptions[opt.PortConstraints.identifier] = opt.PortConstraints(
            value="FIXED_SIDE"
        ).value


class Join(Node):
    shape: Symbol = symbols.Rect(width=50, height=10)
    _css_classes = ["activity-filled"]


class StartActivity(Node):
    shape: Symbol = symbols.Use(value="initial-state", width=12, height=12)


class EndActivity(Node):
    shape: Symbol = symbols.Use(value="final-state", width=12, height=12)


class SimpleArrow(Edge):
    shape_end: str = "arrow"


class ActivityDiagram(Partition):
    # TODO flesh out ideas of encapsulating diagram defs / styles / elements
    defs: Dict[str, Def] = {
        "initial-state": Def(children=[symbols.Circle(radius=6)]),
        "final-state": shapes.DoubleCircle(radius=6),
        "exit-state": shapes.XCircle(radius=6),
        "arrow": connectors.StraightArrow(r=4),
    }
    style: Dict[str, Dict] = {
        " .final-state > g:nth-child(2)": {
            "fill": "var(--jp-elk-node-stroke)",
        },
        " .activity-filled .elknode": {
            "fill": "var(--jp-elk-node-stroke)",
        },
        " .activity-container > .elknode": {
            "rx": "var(--jp-code-font-size)",
        },
    }
    default_edge: Type[Edge] = Field(default=SimpleArrow)
