# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from .svg import Circle, Def, Path, Point


def DoubleCircle(r=6):
    return Def(
        children=[
            Circle(radius=r, position=Point(r, r)),
            Circle(radius=r / 2, position=Point(r, r)),
        ]
    )


def SingleCircle(r=6):
    return Def(
        children=[
            Circle(radius=r, position=Point(r, r)),
        ]
    )


def XCircle(r=6):
    return Def(
        children=[
            Circle(radius=r, position=Point(r, r)),
            Path(
                segments=[
                    Point(r + r * 2 ** -0.5, r + r * 2 ** -0.5),
                    Point(r - r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
            Path(
                segments=[
                    Point(r - r * 2 ** -0.5, r + r * 2 ** -0.5),
                    Point(r + r * 2 ** -0.5, r - r * 2 ** -0.5),
                ]
            ),
        ]
    )


def Diamond(r=6):
    return Def(
        children=[
            Path(
                segments=[
                    Point(0, r),
                    Point(r, 2 * r),
                    Point(2 * r, r),
                    Point(r, 0),
                ],
                closed=True,
            )
        ],
    )
