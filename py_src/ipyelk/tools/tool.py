# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W
import traitlets as T

from ..pipes import MarkElementWidget, Pipe


class Tool(W.Widget):
    tee:Pipe = T.Instance(Pipe, allow_none=True).tag(sync=True, **W.widget_serialization)
    on_done = T.Any(allow_none=True)  # callback when done
    disable = T.Bool(default_value=False).tag(sync=True, **W.widget_serialization)

    async def handler(self):
        """Handler callback for running the tool"""
        # mark clamped pipe as dirty

        # do work

        # callback


class Loader(Tool):
    def load(self) -> MarkElementWidget:
        pass
