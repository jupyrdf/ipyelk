# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
"""Logic Gate Definitions

Based on https://upload.wikimedia.org/wikipedia/commons/c/cb/Circuit_elements.svg

"""

from dataclasses import dataclass
from typing import ClassVar, Dict, List
from uuid import uuid4

from ...diagram import layout_options as opt
from ...diagram.symbol import Def, Symbol, symbols


@dataclass
class Gate(Symbol):
    ports: ClassVar[Dict] = {"a": "WEST", "b": "WEST", "out": "EAST"}
    width: ClassVar[float] = None
    height: ClassVar[float] = None
    type = "node:use"

    def get_shape_props(self) -> Dict:
        return {
            "use": self.identifier,
        }

    def get_labels(self, id=None) -> List:
        return [
            {
                "id": f"{uuid4()}",
                "text": f"{self.__class__.__name__}",
                "layoutOptions": opt.OptionsWidget(
                    options=[
                        opt.NodeLabelPlacement(
                            horizontal="center", vertical="bottom", inside=False
                        )
                    ]
                ).value,
            },
        ]

    def get_ports(self, id=None) -> List:
        return [
            {
                "id": f"{id}.{key}",
                "width": 0.1,
                "height": 0.1,
                "layoutOptions": opt.OptionsWidget(
                    options=[opt.PortSide(value=value)]
                ).value,
            }
            for key, value in self.ports.items()
        ]

    def get_layoutOptions(self) -> Dict:
        return opt.OptionsWidget(
            options=[
                opt.PortConstraints(value="FIXED_SIDE"),
                opt.NodeSizeConstraints(
                    node_labels=False, ports=False, port_labels=False, minimun_size=True
                ),
                opt.NodeSizeMinimum(width=int(self.width), height=int(self.height)),
            ]
        ).value


class XOR_Gate(Gate):
    identifier = "xor_gate"
    width = 36
    height = 26
    shape = Def(
        children=[
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                221.07742, 179.18841 C 251.75683,179.18841 255.13373,193.04183
                255.13373,193.04183 C 250.65971,209.43137 220.99496,206.81278
                220.99496,206.81278 C 235.17822,192.95936 221.07742,179.18841
                221.07742,179.18841 z
                ""/>""",
                x=-219.5,
                y=-180,
            ),
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                215.71747,180.2604 C 226.02507,193.20675 215.71747,205.90571
                215.71747,205.90571"/>""",
                x=-219.5,
                y=-180,
            ),
        ],
        width=36,
        height=26,
    )


class And_Gate(Gate):
    identifier = "and_gate"
    shape = Def(
        children=[
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                291.82342,319.35468  L 291.82342,346.31327 C 337.96707,348.73263
                339.04172,316.76251 291.82342,319.35468 z "/>""",
                x=-291.5,
                y=-319.7,
            )
        ],
        width=36,
        height=26,
    )
    width = 36
    height = 26


class Or_Gate(Gate):
    identifier = "or_gate"
    shape = Def(
        children=[
            symbols.SVG(
                value="""<path d="M 286.89693,404.03872 C 317.57634,404.03872
                320.95324,417.89214 320.95324,417.89214 C 316.47922,434.28168
                286.81447,431.66309 286.81447,431.66309 C 300.99773,417.80967
                286.89693,404.03872 286.89693,404.03872 z " />""",
                x=-292.25,
                y=-405,
            )
        ],
        width=29,
        height=26,
    )
    width = 29
    height = 26


class Nor_Gate(Gate):
    identifier = "nor_gate"
    shape = Def(
        children=[
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                286.50598,446.11044 C 317.18539,446.11044 320.56229,459.96386
                320.56229,459.96386 L 320.47983,459.96386 C 316.08827,476.3534
                286.42352,473.73481 286.42352,473.73481 C 300.60678,459.88139
                286.50598,446.11044 286.50598,446.11044 z "/>""",
                x=-292,
                y=-447,
            ),
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M 254.10886
                234.75238 A 4.7229962 4.7229962 0 1 1  244.66287,234.75238 A
                4.7229962 4.7229962 0 1 1  254.10886 234.75238 z"
                transform="matrix(0.6499792,0,0,0.6499792,161.84911,307.54743)"/>""",
                x=-292,
                y=-447,
            ),
        ],
        width=35.3,
        height=26,
    )
    width = 35.3
    height = 26


class Nand_Gate(Gate):
    identifier = "nand_gate"
    shape = Def(
        children=[
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                219.98902,54.008713 L 219.98902,80.967304 C 266.13267,83.386665
                267.20732,51.416541 219.98902,54.008713 z "/>""",
                x=-219.5,
                y=-55,
            ),
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M 254.10886
                234.75238 A 4.7229962 4.7229962 0 1 1  244.66287,234.75238 A
                4.7229962 4.7229962 0 1 1  254.10886 234.75238 z"/>""",
                x=-209,
                y=-221.5,
            ),
        ],
        width=45.4,
        height=26,
    )
    width = 45.4
    height = 26


class Not_Gate(Gate):
    identifier = "not_gate"
    shape = Def(
        children=[
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                291.48301,543.49359 L 291.48301,528.99086 L 315.53386,542.87663
                L 291.49576,556.85361 z"/>""",
                # x=-291,
                # y=-530,
            ),
            symbols.SVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M 254.10886
                234.75238 A 4.7229962 4.7229962 0 1 1  244.66287,234.75238 A
                4.7229962 4.7229962 0 1 1  254.10886 234.75238 z"
                transform="translate(71.734249,308.16985)"/>""",
                # x=-291,
                # y=-530,
            ),
        ],
        x=291,
        y=530,
        width=35,
        height=26,
    )
    width = 35
    height = 26
    ports = {"in": "WEST", "out": "EAST"}
