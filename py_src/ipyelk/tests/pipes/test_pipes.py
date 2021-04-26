import pytest

from ipyelk.pipes import MarkElementWidget, Pipe


@pytest.mark.asyncio
async def test_pipe_instances():
    p = Pipe()
    p.source = MarkElementWidget()
    value = await p.run()
    assert p.value is value
    assert p.value is p.source
