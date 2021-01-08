# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...diagram.symbol import Def, symbols


def DoubleCircle(radius=6):
    return Def(
        children=[
            symbols.Circle(radius=radius),
            symbols.Circle(radius=radius / 2, x=radius, y=radius),
        ]
    )


def XCircle(radius=6):
    r = radius
    return Def(
        children=[
            symbols.Circle(radius=r),
            symbols.Path.from_list(
                [
                    (r + r * 2 ** -0.5, r + r * 2 ** -0.5),
                    (r - r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
            symbols.Path.from_list(
                [
                    (r - r * 2 ** -0.5, r + r * 2 ** -0.5),
                    (r + r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
        ]
    )
