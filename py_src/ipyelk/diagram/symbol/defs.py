# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict

from ipywidgets import DOMWidget
from pydantic import Field

# from .elk_model import ElkNode
from .symbols import Point, Symbol


class Def(Symbol):
    type = "def"
    # TODO should def strip `id` out of the `to_json` result?


class ConnectorDef(Def):
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


def defs_to_json(defs: Dict[str, Def], widget: DOMWidget):
    """[summary]

    :param defs: [description]
    :type defs: Dict[str, Def]
    :param diagram: [description]
    :type diagram: [type]
    :return: [description]
    :rtype: [type]
    """
    return {f"{k}": v.to_json() for k, v in defs.items()}


def_serialization = {"to_json": defs_to_json}
