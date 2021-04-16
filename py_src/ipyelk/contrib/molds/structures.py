# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...elements import ElementProperties, Node, shapes


def DoubleCircle(radius=6):
    return Node(
        children=[
            Node(properties=ElementProperties(shape=shapes.Circle(radius=6))),
            Node(
                properties=ElementProperties(
                    shape=shapes.Circle(radius=3, x=radius, y=radius)
                )
            ),
        ]
    )


def XCircle(radius=6) -> Node:
    r = radius
    return Node(
        children=[
            Node(properties=ElementProperties(shape=shapes.Circle(radius=r))),
            Node(
                properties=ElementProperties(
                    shape=shapes.Path.from_list(
                        [
                            (r + r * 2 ** -0.5, r + r * 2 ** -0.5),
                            (r - r * 2 ** -0.5, r - r * 2 ** -0.5),
                        ]
                    )
                )
            ),
            Node(
                properties=ElementProperties(
                    shape=shapes.Path.from_list(
                        [
                            (r - r * 2 ** -0.5, r + r * 2 ** -0.5),
                            (r + r * 2 ** -0.5, r - r * 2 ** -0.5),
                        ]
                    )
                )
            ),
        ]
    )
