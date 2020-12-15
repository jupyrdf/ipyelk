# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
"""Logic Gate Definitions

Based on https://upload.wikimedia.org/wikipedia/commons/c/cb/Circuit_elements.svg

"""

from ...diagram import Symbol
from ...diagram import layout_options as opt
from ...diagram.defs.svg import Def, Point, RawSVG


class Gate(Symbol):
    ports = {"a": "WEST", "b": "WEST", "out": "EAST"}

    @property
    def data(self):
        return {
            "properties": {
                "use": self.identifier,
            },
            "width": self.width,
            "height": self.height,
            "labels": [
                {
                    "id": f"{self.id}_label_0",
                    "text": f"{self.id}",
                    "layoutOptions": opt.OptionsWidget(
                        options=[
                            opt.NodeLabelPlacement(
                                horizontal="center", vertical="bottom", inside=False
                            )
                        ]
                    ).value,
                },
            ],
            "layoutOptions": opt.OptionsWidget(
                options=[
                    opt.PortConstraints(value="FIXED_SIDE"),
                ]
            ).value,
            "ports": [
                {
                    "id": f"{self.id}.{key}",
                    "width": 0.1,
                    "height": 0.1,
                    "layoutOptions": opt.OptionsWidget(
                        options=[opt.PortSide(value=value)]
                    ).value,
                }
                for key, value in self.ports.items()
            ],
        }


class XOR_Gate(Gate):
    identifier = "xor_gate"
    shape = Def(
        children=[
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                221.07742, 179.18841 C 251.75683,179.18841 255.13373,193.04183
                255.13373,193.04183 C 250.65971,209.43137 220.99496,206.81278
                220.99496,206.81278 C 235.17822,192.95936 221.07742,179.18841
                221.07742,179.18841 z
                ""/>""",
                position=Point(-219.5, -180),
            ),
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                215.71747,180.2604 C 226.02507,193.20675 215.71747,205.90571
                215.71747,205.90571"/>""",
                position=Point(-219.5, -180),
            ),
        ]
    )
    width = 36
    height = 26


class And_Gate(Gate):
    identifier = "and_gate"
    shape = Def(
        children=[
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                291.82342,319.35468  L 291.82342,346.31327 C 337.96707,348.73263
                339.04172,316.76251 291.82342,319.35468 z "/>""",
                position=Point(-291.5, -319.7),
            )
        ]
    )
    width = 36
    height = 26


class Or_Gate(Gate):
    identifier = "or_gate"
    shape = Def(
        children=[
            RawSVG(
                value="""<path d="M 286.89693,404.03872 C 317.57634,404.03872
                320.95324,417.89214 320.95324,417.89214 C 316.47922,434.28168
                286.81447,431.66309 286.81447,431.66309 C 300.99773,417.80967
                286.89693,404.03872 286.89693,404.03872 z " />""",
                position=Point(-292.25, -405),
            )
        ]
    )
    width = 29
    height = 26


class Nor_Gate(Gate):
    identifier = "nor_gate"
    shape = Def(
        children=[
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                286.50598,446.11044 C 317.18539,446.11044 320.56229,459.96386
                320.56229,459.96386 L 320.47983,459.96386 C 316.08827,476.3534
                286.42352,473.73481 286.42352,473.73481 C 300.60678,459.88139
                286.50598,446.11044 286.50598,446.11044 z "/>""",
                position=Point(-292, -447),
            ),
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M 254.10886
                234.75238 A 4.7229962 4.7229962 0 1 1  244.66287,234.75238 A
                4.7229962 4.7229962 0 1 1  254.10886 234.75238 z"
                transform="matrix(0.6499792,0,0,0.6499792,161.84911,307.54743)"/>""",
                position=Point(-292, -447),
            ),
        ]
    )
    width = 35.3
    height = 26


class Nand_Gate(Gate):
    identifier = "nand_gate"
    shape = Def(
        children=[
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                219.98902,54.008713 L 219.98902,80.967304 C 266.13267,83.386665
                267.20732,51.416541 219.98902,54.008713 z "/>""",
                position=Point(-219.5, -55),
            ),
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M 254.10886
                234.75238 A 4.7229962 4.7229962 0 1 1  244.66287,234.75238 A
                4.7229962 4.7229962 0 1 1  254.10886 234.75238 z"/>""",
                position=Point(-209, -221.5),
            ),
        ]
    )
    width = 45.4
    height = 26


class Not_Gate(Gate):
    identifier = "not_gate"
    shape = Def(
        children=[
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M
                291.48301,543.49359 L 291.48301,528.99086 L 315.53386,542.87663
                L 291.49576,556.85361 z"/>""",
                position=Point(-291, -530),
            ),
            RawSVG(
                value="""<path xmlns="http://www.w3.org/2000/svg" d="M 254.10886
                234.75238 A 4.7229962 4.7229962 0 1 1  244.66287,234.75238 A
                4.7229962 4.7229962 0 1 1  254.10886 234.75238 z"
                transform="translate(71.734249,308.16985)"/>""",
                position=Point(-291, -530),
            ),
        ]
    )
    width = 35
    height = 26
    ports = {"in": "WEST", "out": "EAST"}
