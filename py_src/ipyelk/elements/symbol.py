# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict

from pydantic import BaseModel, Field

from .elements import Node
from .shapes import Point


class Symbol(BaseModel):
    identifier: str = Field(
        ..., description="Unique identifier for uses of this symbol to reference"
    )
    element: Node = Field(..., description="Root element for the symbol")
    width: float = Field(..., title="Width", description="Viewbox width")
    height: float = Field(..., title="Height", description="Viewbox height")
    x: float = Field(0, title="X", description="Viewbox X Position")
    y: float = Field(0, title="Y", description="Viewbox Y Position")


class EndpointSymbol(Symbol):
    path_offset: Point = Field(
        default_factory=Point, description="Moves the endpoint of the path"
    )
    symbol_offset: Point = Field(
        default_factory=Point, description="Moves the origin of the symbol"
    )
    width: float = Field(0, title="Width", description="Viewbox width")
    height: float = Field(0, title="Height", description="Viewbox height")


class SymbolSpec(BaseModel):
    """A set of symbols with unique identifiers"""

    library: Dict[str, Symbol] = Field(
        default_factory=dict,
        description="Mapping of unique symbol identifiers to a symbol",
    )

    def add(self, *symbols: Symbol) -> "SymbolSpec":
        """Add a series of symbols to the library

        :return: current SymbolSpec
        """
        for symbol in symbols:
            assert (
                symbol.identifier not in self.library
            ), f"Identifier should be unique. {symbol.identifier} is duplicated"
            self.library[symbol.identifier] = symbol
        return self

    def __getitem__(self, key: str) -> str:
        """Test is key is an identifier for a symbol in the library and returns
        that key

        :param key: potential symbol identifer
        :return: symbol identifier
        """
        if key not in self.library:
            raise KeyError(
                f"`{key}` is not a symbol identifier currently in the library"
            )
        return key

    def merge(self, *specs: "SymbolSpec") -> "SymbolSpec":
        """Merge a series of `SymbolSpec`s into a new `SymbolSpec`

        :param specs: series of `SymbolSpecs`
        :return: new SymbolSpec
        """
        new = SymbolSpec()
        new.add(*self.library.values())
        for spec in specs:
            new.add(*spec.library.values())
        return new
