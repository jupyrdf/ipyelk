# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Kernel side of the ``action: stale`` re-sync protocol.

These are kernel unit checks of the protocol contract only: a stale report
re-emits widget state (throttled) and leaves the pending roundtrip alone.
They do not exercise a browser or jupyter-server's iopub rate limiter.
"""

import asyncio
from time import monotonic

import pytest

from ipyelk.diagram.viewer import Viewer
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes.elkjs import ElkJS
from ipyelk.pipes.text_sizer import BrowserTextSizer
from ipyelk.pipes.util import resync_stale


def _synced(cls):
    pipe = cls(timeout=5.0)
    pipe.inlet = MarkElementWidget()
    pipe.outlet = MarkElementWidget()
    return pipe


def _record_state(widget, name, into):
    widget.send_state = lambda *_a, **_k: into.append(name)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", [ElkJS, BrowserTextSizer])
async def test_stale_report_resyncs_state_and_keeps_the_roundtrip_alive(cls):
    pipe = _synced(cls)
    synced = []
    for name in ("pipe", "inlet", "outlet"):
        _record_state(pipe if name == "pipe" else getattr(pipe, name), name, synced)
    # a previous run left the throttle wide open; a new roundtrip must reset it
    pipe._stale_resync_at = monotonic()
    pipe._stale_resync_interval = 1e9

    sends = []

    def fake_send(content, *_args, **_kwargs):
        sends.append(content)
        if len(sends) == 1:
            # frontend got the run request but its inlet value never arrived
            pipe._handle_browser_msg(
                pipe, {"action": "stale", "missing": {"value": True}}, None
            )
        else:
            # re-synced frontend serves the re-sent request
            pipe.outlet.value = Node()

    pipe.send = fake_send

    await asyncio.wait_for(pipe.run(), timeout=3.0)

    # a trailing 'outlet' may follow: run() persists the outlet on finish
    assert synced[:3] == ["pipe", "inlet", "outlet"]
    assert sends == [{"action": "run"}, {"action": "run"}]
    assert pipe._roundtrip_future is None
    assert pipe._stale_resync_interval == pytest.approx(2.0)
    pipe.close()


def test_stale_report_is_throttled_with_doubling_interval():
    pipe = _synced(ElkJS)
    synced = []
    for name in ("pipe", "inlet", "outlet"):
        _record_state(pipe if name == "pipe" else getattr(pipe, name), name, synced)

    stale = {"action": "stale"}
    pipe._handle_browser_msg(pipe, stale, None)
    pipe._handle_browser_msg(pipe, stale, None)  # within the 2s window
    assert synced == ["pipe", "inlet", "outlet"]
    assert pipe._stale_resync_interval == pytest.approx(2.0)

    pipe._stale_resync_at = 0.0  # step past the window
    pipe._handle_browser_msg(pipe, stale, None)
    assert len(synced) == 6
    assert pipe._stale_resync_interval == pytest.approx(4.0)  # doubles

    pipe.close()


@pytest.mark.asyncio
async def test_stale_report_is_not_an_error():
    pipe = _synced(ElkJS)
    for w in (pipe, pipe.inlet, pipe.outlet):
        _record_state(w, "x", [])

    future = asyncio.get_running_loop().create_future()
    pipe._roundtrip_future = future
    pipe._handle_browser_msg(pipe, {"action": "stale"}, None)
    assert not future.done()
    future.cancel()
    pipe.close()


@pytest.mark.parametrize("widget_type", [Viewer, ElkJS])
def test_resync_throttles_are_independent_per_widget(widget_type, monkeypatch):
    monkeypatch.setattr("ipyelk.pipes.util.monotonic", lambda: 10.0)
    first, second = widget_type(), widget_type()
    sent = []
    _record_state(first, "first", sent)
    _record_state(second, "second", sent)
    try:
        assert resync_stale(first)
        assert not resync_stale(first)
        assert second._stale_resync_at == pytest.approx(0.0)
        assert second._stale_resync_interval == pytest.approx(0.0)
        assert resync_stale(second)
        assert sent == ["first", "second"]
    finally:
        first.close()
        second.close()


def test_resync_stale_uses_custom_interval_bounds(monkeypatch):
    ticks = iter((10.0, 12.0, 13.0, 17.0, 18.0))
    monkeypatch.setattr("ipyelk.pipes.util.monotonic", lambda: next(ticks))
    viewer = Viewer()
    sent = []
    _record_state(viewer, "viewer", sent)
    try:
        assert [
            resync_stale(viewer, None, min_interval=3.0, max_interval=5.0)
            for _ in range(5)
        ] == [True, False, True, False, True]
        assert viewer._stale_resync_interval == pytest.approx(5.0)
        assert sent == ["viewer"] * 3
    finally:
        viewer.close()


def test_viewer_stale_report_resyncs_view_wiring():
    viewer = Viewer()
    synced = []
    _record_state(viewer, "viewer", synced)

    stale = {"action": "stale", "missing": {"source": True}}
    viewer._handle_browser_msg(viewer, stale, None)
    assert synced == ["viewer"]  # no source wired yet
    viewer._handle_browser_msg(viewer, stale, None)
    assert synced == ["viewer"]  # throttled

    viewer.source = MarkElementWidget()  # rewiring resets the throttle
    _record_state(viewer.source, "source", synced)
    synced.clear()
    viewer._handle_browser_msg(viewer, {"action": "stale"}, None)
    assert synced == ["viewer", "source"]

    viewer._handle_browser_msg(viewer, {"action": "center"}, None)
    viewer._handle_browser_msg(viewer, "not-a-dict", None)
    assert synced == ["viewer", "source"]
    viewer.close()
