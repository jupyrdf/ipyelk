# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio

import ipywidgets as W
import traitlets as T

from ..pipes import Pipe
from .tool import Tool


class PipelineProgressBar(Tool):
    bar = T.Instance(W.FloatProgress, kw={})
    pipe = T.Instance(Pipe)
    priority = T.Int(default_value=100)
    #: delays (s) after a terminal update at which the bar's state is re-sent:
    #: the hide/fill is a fire-and-forget state update with no retransmit, and
    #: a congested iopub channel that drops it leaves a zombie bar on screen.
    #: Two echoes heal the common case; they are not a delivery guarantee.
    echo_delays: tuple[float, ...] = (2.0, 10.0)
    _echo_handles: tuple[asyncio.TimerHandle, ...] = ()

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

        self._cancel_echoes()
        if bar.value >= bar.max:
            self._schedule_echoes()

    def _cancel_echoes(self):
        for handle in self._echo_handles:
            handle.cancel()
        self._echo_handles = ()

    def _schedule_echoes(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no running loop to schedule delayed echoes on
        self._echo_handles = tuple(
            loop.call_later(delay, self._echo_terminal_state)
            for delay in self.echo_delays
        )

    def _echo_terminal_state(self):
        bar = self.bar
        if bar.comm is not None and bar.value >= bar.max:
            bar.send_state()
            bar.layout.send_state()

    def close(self):
        self._cancel_echoes()
        super().close()
