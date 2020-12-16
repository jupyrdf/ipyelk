# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...diagram.defs import Circle, ConnectorDef, Path, Point


def Rhomb(r=6):
    return ConnectorDef(
        children=[
            Path(
                segments=[
                    Point(0, 0),
                    Point(r, r / 2),
                    Point(2 * r, 0),
                    Point(r, -r / 2),
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
                position=Point(r, 0),
            ),
            Path(segments=[Point(0, 0), Point(2 * r, 0)]),
            Path(segments=[Point(r, -r), Point(r, r)]),
        ],
        correction=Point(-1, 0),
        offset=Point(-2 * r, 0),
    )


def StraightArrow(r=6, closed=False):
    return ConnectorDef(
        children=[
            Path(segments=[Point(r, -r), Point(0, 0), Point(r, r)], closed=closed),
        ],
        correction=Point(-1, 0),
        offset=Point(-r - 1, 0) if closed else Point(-1, 0),
    )


def ThinArrow(r=6, closed=False):
    return ConnectorDef(
        children=[
            Path(
                segments=[Point(r, -r / 2), Point(0, 0), Point(r, r / 2)], closed=closed
            ),
        ],
        correction=Point(-1, 0),
        offset=Point(-r, 0) if closed else Point(-1, 0),
    )


def FatArrow(r=6, closed=False):
    return ConnectorDef(
        children=[
            Path(
                segments=[Point(r / 2, -r), Point(0, 0), Point(r / 2, r)], closed=closed
            ),
        ],
        correction=Point(-1, 0),
        offset=Point(-r / 2, 0) if closed else Point(-1, 0),
    )


def Space(r=6):
    return ConnectorDef(children=[], offset=Point(-r, 0))
