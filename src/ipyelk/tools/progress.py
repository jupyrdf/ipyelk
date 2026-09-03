# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T

from ..pipes import Pipe
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

        bar.value = pipe.get_progress_value()
        bar.max = 1

        if pipe.status.exception:
            # the run is over: fill the bar and leave it visible as a
            # warning instead of an eternally "in progress" sliver
            bar.value = bar.max
            bar.bar_style = "warning"
            bar.layout.visibility = "visible"
        elif bar.value == bar.max:
            bar.bar_style = ""
            bar.layout.visibility = "hidden"
        else:
            bar.bar_style = ""
            bar.layout.visibility = "visible"
