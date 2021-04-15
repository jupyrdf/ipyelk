# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict, List

from ipywidgets import DOMWidget
from pydantic import BaseModel, Field

from .elements import ElementProperties, ElementShape, Node, Port
from .shapes import Point


class Symbol(BaseModel):
    identifier: str = Field(
        ..., description="Unique identifier for uses of this symbol to reference"
    )
    element: Node = Field(..., description="Root element for the symbol")
    width: float = Field(..., title="Width", description="Viewbox width")
    height: float = Field(..., title="Height", description="Viewbox width")
    x: float = Field(0, title="X", description="Viewbox X Position")
    y: float = Field(0, title="Y", description="Viewbox Y Position")

    @classmethod
    def make_defs(cls, symbols: List["Symbol"]) -> Dict[str, "Symbol"]:
        """Take a list of symbols and return the def dictionary

        :param classes: Subclasses of Shape. If `None` use the subclasses of
        the current class.
        :return: Def Dictionary
        """
        library = {}
        for instance in symbols:
            assert (
                instance.identifier not in library
            ), f"Identifier should be unique. {instance.identifier} is duplicated"
            library[instance.identifier] = instance
        return library

    def node(self, **kwargs) -> Node:
        """Create a Node element that uses this symbol"""
        # todo better merging of defaults against the given kwargs
        return Node(
            properties=ElementProperties(
                shape=ElementShape(
                    type="node:use",
                    use=self.identifier,
                )
            ),
            width=self.width,
            height=self.height,
            **kwargs,
        )

    def port(self, **kwargs) -> Port:
        """Create a Port element that uses this symbol"""
        # todo better merging of defaults against the given kwargs
        return Port(
            properties=ElementProperties(
                shape=ElementShape(
                    use=self.identifier,
                )
            ),
            width=self.width,
            height=self.height,
            **kwargs,
        )


class ConnectorDef(Symbol):
    offset: Point = Field(
        default_factory=Point, description="Moves the endpoint of the path"
    )
    correction: Point = Field(
        default_factory=Point, description="Moves the origin of the symbol"
    )
    width: float = 0
    height: float = 0

    def to_json(self):
        data = super().to_json()
        data.update(
            {
                "offset": self.offset.dict(),
                "correction": self.correction.dict(),
            }
        )
        return data


def symbols_to_json(symbols: Dict[str, Symbol], widget: DOMWidget):
    """[summary]

    :param defs: [description]
    :type defs: Dict[str, Def]
    :param diagram: [description]
    :type diagram: [type]
    :return: [description]
    :rtype: [type]
    """
    return {f"{k}": v.dict(exclude_none=True) for k, v in symbols.items()}


symbol_serialization = {"to_json": symbols_to_json}
