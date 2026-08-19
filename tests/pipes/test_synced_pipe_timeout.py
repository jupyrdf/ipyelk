# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio

import pytest

from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes.elkjs import ElkJS


@pytest.mark.asyncio
async def test_elkjs_times_out_when_browser_never_responds():
    pipe = ElkJS(timeout=0.05)
    pipe.inlet = MarkElementWidget()
    pipe.outlet = MarkElementWidget()

    # Never simulate a browser response -> should time out, not hang.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(pipe.run(), timeout=2.0)


@pytest.mark.asyncio
async def test_elkjs_completes_when_browser_responds():
    pipe = ElkJS(timeout=5.0)
    pipe.inlet = MarkElementWidget()
    pipe.outlet = MarkElementWidget()

    async def fake_browser():
        # Simulate the browser writing the laid-out value back.
        await asyncio.sleep(0.01)
        pipe.outlet.value = Node()

    browser = asyncio.create_task(fake_browser())
    await pipe.run()  # must return without raising
    await browser  # surface any exception from the fake browser
