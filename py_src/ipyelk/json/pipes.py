# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict

import traitlets as T

from .. import diagram

# from ..schema.validator import validate_elk_json
from ..elements import from_elkjson
from ..pipes import BrowserTextSizer, ElkJS, MarkElementWidget, Pipe, Pipeline
from ..tools import Loader


class ElkJSONLoader(Loader):
    def load(self, data: Dict) -> MarkElementWidget:
        return MarkElementWidget(value=from_elkjson(data))


class ElkJSONPipe(Pipe):
    """ Transform data into the form required by the Diagram. """

    _version: str = "v1"

    inlet = T.Dict()  # could be elkjson schema validator

    async def run(self) -> MarkElementWidget:
        """Generate elk json"""
        self.outlet.value = from_elkjson(self.inlet)
        return self.outlet


class ELKJSONPipeline(Pipeline):
    inlet = T.Dict()  # could be elkjson schema validator

    @T.default("pipes")
    def _default_Pipes(self):
        return [
            ElkJSONPipe(),
            BrowserTextSizer(),
            ElkJS(),
        ]


class Diagram(diagram.Diagram):
    @T.default("pipe")
    def _default_Pipe(self):
        return ELKJSONPipeline()
