# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...elements import Node, NodeProperties, shapes


def DoubleCircle(radius=6):
    return Node(
        children=[
            Node(properties=NodeProperties(shape=shapes.Circle(radius=6))),
            Node(
                properties=NodeProperties(
                    cssClasses="inner-circle",
                    shape=shapes.Circle(radius=3, x=radius, y=radius),
                )
            ),
        ]
    )


def XCircle(radius=6) -> Node:
    r = radius
    return Node(
        children=[
            Node(properties=NodeProperties(shape=shapes.Circle(radius=r))),
            Node(
                properties=NodeProperties(
                    shape=shapes.Path.from_list(
                        [
                            (r + r * 2 ** -0.5, r + r * 2 ** -0.5),
                            (r - r * 2 ** -0.5, r - r * 2 ** -0.5),
                        ]
                    )
                )
            ),
            Node(
                properties=NodeProperties(
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
