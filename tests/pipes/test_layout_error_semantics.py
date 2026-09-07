# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio

import pytest

from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes.base import PipeDisposition, PipeStatus
from ipyelk.pipes.elkjs import ElkJS
from ipyelk.pipes.text_sizer import BrowserTextSizer


def _synced(cls):
    pipe = cls(timeout=5.0)
    pipe.inlet = MarkElementWidget()
    pipe.outlet = MarkElementWidget()
    return pipe


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", [ElkJS, BrowserTextSizer])
async def test_browser_error_stops_the_roundtrip(cls):
    """An errored browser run must stop the retries, not feed them."""
    pipe = _synced(cls)

    sends = []
    pipe.send = lambda content, *_args, **_kwargs: sends.append(content)

    async def browser_rejects():
        await asyncio.sleep(0.05)
        pipe._handle_browser_msg(
            pipe,
            {"action": "error", "error": "Id must be a string or an integer: null"},
            None,
        )

    browser = asyncio.create_task(browser_rejects())
    with pytest.raises(RuntimeError, match="Id must be a string"):
        await asyncio.wait_for(pipe.run(), timeout=2.0)
    await browser

    # the error rejected the pending roundtrip before any resend
    assert sends == [{"action": "run"}]
    assert pipe._roundtrip_future is None


@pytest.mark.asyncio
async def test_run_resends_until_a_frontend_answers():
    """A run request sent before any frontend attached must be re-sent."""
    pipe = _synced(ElkJS)

    sends = []

    def fake_send(content, *args, **kwargs):
        sends.append(content)
        if len(sends) == 2:
            # the second request finds an attached frontend and is answered
            pipe.outlet.value = Node()

    pipe.send = fake_send

    await asyncio.wait_for(pipe.run(), timeout=3.0)
    assert len(sends) == 2


def test_error_disposition_is_terminal_progress():
    from datetime import datetime

    status = PipeStatus.error(start_time=datetime.now(), exception=ValueError("x"))
    assert status.disposition == PipeDisposition.error
    assert status.step() == 1
