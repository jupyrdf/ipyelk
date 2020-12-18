# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...diagram.defs import Def
from ...diagram.symbol import Circle, Path


def DoubleCircle(r=6):
    return Def(
        children=[
            Circle(radius=r),
            Circle(radius=r / 2, x=r, y=r),
        ]
    )


def XCircle(r=6):
    return Def(
        children=[
            Circle(radius=r),
            Path.from_list(
                [
                    (r + r * 2 ** -0.5, r + r * 2 ** -0.5),
                    (r - r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
            Path.from_list(
                [
                    (r - r * 2 ** -0.5, r + r * 2 ** -0.5),
                    (r + r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
        ]
    )
