# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...diagram.shape import Symbol, shapes


def DoubleCircle(radius=6):
    return Symbol(
        children=[
            shapes.Circle(radius=radius),
            shapes.Circle(radius=radius / 2, x=radius, y=radius),
        ]
    )


def XCircle(radius=6):
    r = radius
    return Symbol(
        children=[
            shapes.Circle(radius=r),
            shapes.Path.from_list(
                [
                    (r + r * 2 ** -0.5, r + r * 2 ** -0.5),
                    (r - r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
            shapes.Path.from_list(
                [
                    (r - r * 2 ** -0.5, r + r * 2 ** -0.5),
                    (r + r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
        ]
    )
