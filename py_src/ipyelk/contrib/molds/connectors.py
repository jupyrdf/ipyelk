# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...elements import Node, NodeProperties

# from ...diagram.shapes.shapes import Circle, Path, Point
from ...elements.shapes import Circle, Path, Point
from ...elements.symbol import EndpointSymbol


def Rhomb(identifier: str, r: float = 6) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=NodeProperties(
                shape=Path.from_list(
                    [
                        (0, 0),
                        (r, r / 2),
                        (2 * r, 0),
                        (r, -r / 2),
                    ],
                    closed=True,
                )
            ),
        ),
        symbol_offset=Point(x=-1, y=0),
        path_offset=Point(x=-2 * r, y=0),
    )


def Containment(identifier: str, r=6) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            children=[
                Node(
                    properties=NodeProperties(
                        shape=Circle(
                            radius=r,
                            x=r,
                            y=0,
                        )
                    )
                ),
                Node(
                    properties=NodeProperties(
                        shape=Path.from_list([(0, 0), (2 * r, 0)]),
                    )
                ),
                Node(
                    properties=NodeProperties(
                        shape=Path.from_list([(r, -r), (r, r)]),
                    )
                ),
            ]
        ),
        symbol_offset=Point(x=-1, y=0),
        path_offset=Point(x=-2 * r, y=0),
    )


def StraightArrow(identifier: str, r=6, closed=False) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=NodeProperties(
                shape=Path.from_list([(r, -r), (0, 0), (r, r)], closed=closed),
            )
        ),
        symbol_offset=Point(x=-1, y=0),
        path_offset=Point(x=-r - 1, y=0) if closed else Point(x=-1, y=0),
    )


def ThinArrow(identifier: str, r=6, closed=False) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=NodeProperties(
                shape=Path.from_list([(r, -r / 2), (0, 0), (r, r / 2)], closed=closed),
            )
        ),
        symbol_offset=Point(x=-1, y=0),
        path_offset=Point(x=-r, y=0) if closed else Point(x=-1, y=0),
    )


def FatArrow(identifier: str, r=6, closed=False) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=NodeProperties(
                shape=Path.from_list([(r / 2, -r), (0, 0), (r / 2, r)], closed=closed),
            )
        ),
        symbol_offset=Point(x=-1, y=0),
        path_offset=Point(x=-r / 2, y=0) if closed else Point(x=-1, y=0),
    )


def Space(identifier: str, r=6) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier, element=Node(), path_offset=Point(x=-r, y=0)
    )
