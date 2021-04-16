# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...elements import ElementProperties, Node

# from ...diagram.shapes.shapes import Circle, Path, Point
from ...elements.shapes import Circle, Path, Point
from ...elements.symbol import EndpointSymbol


def Rhomb(identifier: str, r: float = 6) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=ElementProperties(
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
        correction=Point(x=-1, y=0),
        offset=Point(x=-2 * r, y=0),
    )


def Containment(identifier: str, r=6) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            children=[
                Node(
                    properties=ElementProperties(
                        shape=Circle(
                            radius=r,
                            x=r,
                            y=0,
                        )
                    )
                ),
                Node(
                    properties=ElementProperties(
                        shape=Path.from_list([(0, 0), (2 * r, 0)]),
                    )
                ),
                Node(
                    properties=ElementProperties(
                        shape=Path.from_list([(r, -r), (r, r)]),
                    )
                ),
            ]
        ),
        correction=Point(x=-1, y=0),
        offset=Point(x=-2 * r, y=0),
    )


def StraightArrow(identifier: str, r=6, closed=False) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=ElementProperties(
                shape=Path.from_list([(r, -r), (0, 0), (r, r)], closed=closed),
            )
        ),
        correction=Point(x=-1, y=0),
        offset=Point(x=-r - 1, y=0) if closed else Point(x=-1, y=0),
    )


def ThinArrow(identifier: str, r=6, closed=False) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=ElementProperties(
                shape=Path.from_list([(r, -r / 2), (0, 0), (r, r / 2)], closed=closed),
            )
        ),
        correction=Point(x=-1, y=0),
        offset=Point(x=-r, y=0) if closed else Point(x=-1, y=0),
    )


def FatArrow(identifier: str, r=6, closed=False) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier,
        element=Node(
            properties=ElementProperties(
                shape=Path.from_list([(r / 2, -r), (0, 0), (r / 2, r)], closed=closed),
            )
        ),
        correction=Point(x=-1, y=0),
        offset=Point(x=-r / 2, y=0) if closed else Point(x=-1, y=0),
    )


def Space(identifier: str, r=6) -> EndpointSymbol:
    return EndpointSymbol(
        identifier=identifier, element=Node(), offset=Point(x=-r, y=0)
    )
