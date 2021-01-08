# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...diagram.symbol.defs import ConnectorDef
from ...diagram.symbol.symbols import Circle, Path, Point


def Rhomb(r=6):
    return ConnectorDef(
        children=[
            Path.from_list(
                [
                    (0, 0),
                    (r, r / 2),
                    (2 * r, 0),
                    (r, -r / 2),
                ],
                closed=True,
            )
        ],
        correction=Point(-1, 0),
        offset=Point(-2 * r, 0),
    )


def Containment(r=6):
    return ConnectorDef(
        children=[
            Circle(
                radius=r,
                x=r,
                y=0,
            ),
            Path.from_list([(0, 0), (2 * r, 0)]),
            Path.from_list([(r, -r), (r, r)]),
        ],
        correction=Point(-1, 0),
        offset=Point(-2 * r, 0),
    )


def StraightArrow(r=6, closed=False):
    return ConnectorDef(
        children=[
            Path.from_list([(r, -r), (0, 0), (r, r)], closed=closed),
        ],
        correction=Point(-1, 0),
        offset=Point(-r - 1, 0) if closed else Point(-1, 0),
    )


def ThinArrow(r=6, closed=False):
    return ConnectorDef(
        children=[
            Path.from_list([(r, -r / 2), (0, 0), (r, r / 2)], closed=closed),
        ],
        correction=Point(-1, 0),
        offset=Point(-r, 0) if closed else Point(-1, 0),
    )


def FatArrow(r=6, closed=False):
    return ConnectorDef(
        children=[
            Path.from_list([(r / 2, -r), (0, 0), (r / 2, r)], closed=closed),
        ],
        correction=Point(-1, 0),
        offset=Point(-r / 2, 0) if closed else Point(-1, 0),
    )


def Space(r=6):
    return ConnectorDef(children=[], offset=Point(-r, 0))
