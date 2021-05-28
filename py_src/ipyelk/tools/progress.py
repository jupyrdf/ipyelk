# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Tuple

import ipywidgets as W
import traitlets as T

from ..pipes import Pipe, PipeDisposition, Pipeline
from .tool import Tool

STEP = {
    PipeDisposition.waiting: 0,
    PipeDisposition.running: 1 / 3,
    PipeDisposition.done: 2 / 3,
}


class PipelineProgressBar(Tool):
    bar = T.Instance(W.FloatProgress, kw={})
    exception = T.Instance(Exception, allow_none=True)
    pipe = T.Instance(Pipe)
    pipeline = T.Instance(Pipeline)
    priority = T.Int(default_value=100)

    @T.default("ui")
    def _default_ui(self):
        return self.bar

    def update(self, pipeline: Pipeline, pipe: Pipe):
        self.pipe = pipe
        self.pipeline = pipeline
        bar = self.bar

        #         bar.description = pipe.__class__.__name__
        bar.tooltip = f"{bar.description} {pipe.disposition}"
        bar.max, bar.value = self.get_progress_value(pipeline, pipe)

        if pipe.disposition is PipeDisposition.error:
            self.exception = pipeline.exception
            bar.bar_style = "warning"
        else:
            bar.bar_style = ""
        if bar.value == bar.max:
            bar.layout.visibility = "hidden"
        else:
            bar.layout.visibility = "visible"

    def get_progress_value(self, pipeline, pipe) -> Tuple[float, float]:
        num_pipes = len(pipeline.pipes)
        current_pipe = pipeline.pipes.index(pipe)
        if current_pipe + 1 == num_pipes and pipe.disposition is PipeDisposition.done:
            value = num_pipes
        else:
            value = current_pipe + STEP.get(pipe.disposition, 0)
        return num_pipes, value
