# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from dataclasses import asdict, dataclass, is_dataclass
from typing import Dict

from ipywidgets import DOMWidget

# from .elk_model import ElkNode
from .symbols import Point, Symbol


@dataclass
class Def(Symbol):
    type = "def"
    # TODO should def strip `id` out of the `to_json` result?


@dataclass
class ConnectorDef(Def):
    type = "connectordef"
    offset: Point = Point()
    correction: Point = Point()

    def to_json(self):
        data = super().to_json()
        offset = asdict(self.offset) if is_dataclass(self.offset) else self.offset
        correction = (
            asdict(self.correction)
            if is_dataclass(self.correction)
            else self.correction
        )
        data.update(
            {
                "offset": offset,
                "correction": correction,
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
