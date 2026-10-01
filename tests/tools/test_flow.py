# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Tools merge their reports into the pending flow instead of replacing it."""

import asyncio

import pytest

from ipyelk.pipes import Pipe
from ipyelk.pipes import flows as F
from ipyelk.tools import Tool


class _Noop(Tool):
    async def run(self):
        pass


@pytest.mark.asyncio
async def test_two_tools_keep_a_pending_flow_in_order_without_duplicates():
    pipe = Pipe()
    pipe.inlet.flow = (F.New,)  # pending: some writer already asked for a full run
    a = _Noop(tee=pipe, reports=(F.Node.layout_options,))
    b = _Noop(tee=pipe, reports=(F.Node.hidden, F.Node.layout_options))

    await asyncio.gather(a.trigger(), b.trigger())

    assert pipe.inlet.flow == (F.New, F.Node.layout_options, F.Node.hidden)


def test_record_reports_without_a_pipe_is_a_noop():
    _Noop(reports=("x",)).record_reports()
