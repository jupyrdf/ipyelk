# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict

from ipywidgets import DOMWidget
from pydantic import Field

# from .elk_model import ElkNode
from .shapes import Point, Shape


class Symbol(Shape):
    type = "def"
    # TODO should def strip `id` out of the `to_json` result?


class ConnectorDef(Symbol):
    type = "connectordef"
    offset: Point = Field(default_factory=Point)
    correction: Point = Field(default_factory=Point)

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
    return {f"{k}": v.to_json() for k, v in symbols.items()}


symbol_serialization = {"to_json": symbols_to_json}
