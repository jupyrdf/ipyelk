# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T

from ..pipes import Pipe, PipeDisposition
from .tool import Tool


class PipelineProgressBar(Tool):
    bar = T.Instance(W.FloatProgress, kw={})
    pipe = T.Instance(Pipe)
    priority = T.Int(default_value=100)

    @T.default("ui")
    def _default_ui(self):
        return self.bar

    def update(self, pipe: Pipe):
        self.pipe = pipe
        bar = self.bar

        #         bar.description = pipe.__class__.__name__
        bar.tooltip = f"{bar.description} {pipe.disposition}"
        bar.value = pipe.get_progress_value()
        bar.max = 1

        if pipe.disposition is PipeDisposition.error:
            bar.bar_style = "warning"
        else:
            bar.bar_style = ""
        if bar.value == bar.max:
            bar.layout.visibility = "hidden"
        else:
            bar.layout.visibility = "visible"
