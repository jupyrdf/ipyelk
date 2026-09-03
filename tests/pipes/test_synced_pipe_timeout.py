# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio

import pytest

from ipyelk.elements import Label, Node, NodeProperties, Port, convert_elkjson
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes.elkjs import ElkJS
from ipyelk.pipes.text_sizer import BrowserTextSizer


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


@pytest.mark.asyncio
async def test_browser_text_sizer_falls_back_during_testing(monkeypatch):
    monkeypatch.setenv("IPYELK_TESTING", "true")
    label = Label(text="fallback")
    pipe = BrowserTextSizer(timeout=0.01)
    pipe.inlet = MarkElementWidget(value=Node(labels=[label]))
    pipe.outlet = MarkElementWidget()

    await asyncio.wait_for(pipe.run(), timeout=2.0)

    assert label.properties.get_shape().width == 80


def test_persist_indexes_new_elements_from_browser_roundtrip():
    old_root = Node(id="root", children=[Node(id="old")])
    new_root = Node(
        id="root", children=[Node(id="old", ports=[Port(id="old.new-port")])]
    )
    widget = MarkElementWidget(value=old_root)
    widget.build_index()

    widget.value = new_root
    widget.persist()

    assert widget.index.elements.get("old.new-port") is new_root.children[0].ports[0]


def test_persist_keeps_hidden_elements_the_browser_never_sees():
    """`Node.dict` drops hidden children, so a value that has been through the
    browser cannot be allowed to shrink the index -- the collapse/expand tool
    has nothing left to un-hide otherwise.
    """
    hidden = Node(id="plot", properties=NodeProperties(hidden=True))
    root = Node(id="root", children=[Node(id="visible", children=[hidden])])
    widget = MarkElementWidget(value=root)
    widget.build_index()

    # what comes back from the browser: hidden elements stripped
    widget.value = convert_elkjson(root.dict())
    widget.persist()

    assert widget.index.elements.get("plot") is hidden
    assert widget.index.root is root
