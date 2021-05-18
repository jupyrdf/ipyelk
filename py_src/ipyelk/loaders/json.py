# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict

from ..diagram import Diagram

# from ..schema.validator import validate_elk_json
from ..elements import convert_elkjson
from ..pipes import MarkElementWidget
from .loader import Loader


class ElkJSONLoader(Loader):
    def load(self, data: Dict) -> MarkElementWidget:
        return MarkElementWidget(
            value=self.apply_layout_defaults(convert_elkjson(data)),
        )


def from_elkjson(data, **kwargs):
    from .json import ElkJSONLoader

    diagram = Diagram(source=ElkJSONLoader().load(data), **kwargs)
    return diagram
