# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T

from .. import diagram

# from ..schema.validator import validate_elk_json
from ..elements.serialization import node_from_elkjson
from ..pipes import ElkJS, MarkElementWidget, Pipe, Pipeline  # , BrowserTextSizer


class ElkJSONPipe(Pipe):
    """ Transform data into the form required by the Diagram. """

    _version: str = "v1"

    source = T.Dict()  # could be elkjson schema validator

    async def run(self) -> MarkElementWidget:
        """Generate elk json"""
        self.value.value = node_from_elkjson(self.source)
        return self.value


class ELKJSONPipeline(Pipeline):
    source = T.Dict()  # could be elkjson schema validator

    @T.default("pipes")
    def _default_Pipes(self):
        return [
            ElkJSONPipe(),
            # BrowserTextSizer(), # TODO get working
            ElkJS(),
        ]


class Diagram(diagram.Diagram):
    @T.default("pipe")
    def _default_Pipe(self):
        return ELKJSONPipeline()
