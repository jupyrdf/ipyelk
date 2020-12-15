# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from dataclasses import asdict, dataclass
from typing import Dict, Tuple

from ipywidgets import DOMWidget


@dataclass
class Point:
    x: float = 0
    y: float = 0


@dataclass
class Dataclass:
    type: str = None
    children: Tuple["SVGElement"] = ()
    # cssClasses: Tuple[str] = ()

    @property
    def type(self) -> str:
        """Returns the name of the class"""
        return self.__class__.__name__.lower()

    @type.setter
    def type(self, value):
        """Setter is required to get the dataclass to work but is only as passthrough"""
        pass


@dataclass
class SVGElement(Dataclass):
    position: Point = Point()


@dataclass
class Circle(SVGElement):
    radius: float = 0


@dataclass
class Rect(SVGElement):
    height: float = 0
    width: float = 0


@dataclass
class Ellipse(SVGElement):
    rx: float = 0
    ry: float = 0


@dataclass
class Path(SVGElement):
    segments: Tuple[Point] = tuple()
    closed: bool = False


@dataclass
class Def(Dataclass):
    position: Point = Point()


@dataclass
class RawSVG(SVGElement):
    value: str = ""


@dataclass
class ConnectorDef(Def):
    offset: Point = Point()
    correction: Point = Point()


def defs_to_json(defs: Dict[str, Def], widget: DOMWidget):
    """[summary]

    :param defs: [description]
    :type defs: Dict[str, Def]
    :param diagram: [description]
    :type diagram: [type]
    :return: [description]
    :rtype: [type]
    """
    return {f"{k}": asdict(v) for k, v in defs.items()}
