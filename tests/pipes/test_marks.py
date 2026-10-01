# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``MarkElementWidget`` send behaviour (#164)."""

import pytest

from ipyelk.elements import Label, Node
from ipyelk.pipes import MarkElementWidget

# on ipywidgets 8.0.x a kernel-side write is only sent to a kernel-attached
# comm (see ``conftest.kernel_attached_comm``)
pytestmark = pytest.mark.usefixtures("kernel_attached_comm")


def capture_sends(widget, monkeypatch):
    sent = []

    def _send(msg, buffers=None):
        sent.append((msg["method"], sorted(msg.get("state", {}))))

    monkeypatch.setattr(widget, "_send", _send)
    return sent


def browser_wire():
    root = Node(id="root", children=[Node(id="a", labels=[Label(id="l", text="A")])])
    wire = root.model_dump()
    wire["children"][0]["labels"][0]["width"] = 12.5
    wire["children"][0]["x"] = 10.0
    wire["$H"] = 123
    return wire


def test_browser_value_write_is_not_resent(monkeypatch):
    outlet = MarkElementWidget()
    sent = capture_sends(outlet, monkeypatch)

    outlet.set_state({"value": browser_wire()})
    assert sent == [], "a browser write must produce neither an echo nor an update"
    assert outlet.value.children[0].x == pytest.approx(10.0)

    outlet.value = Node(id="root", children=[Node(id="b")])
    assert sent == [("update", ["value"])], "a kernel write is sent exactly once"

    # and the lock is released: a later browser write is again silent
    sent.clear()
    outlet.set_state({"value": browser_wire()})
    assert sent == []


def test_other_traits_keep_default_send_behaviour(monkeypatch):
    """Only ``value`` is special-cased; ``flow`` follows the ipywidgets rules."""
    outlet = MarkElementWidget()
    sent = capture_sends(outlet, monkeypatch)

    outlet.flow = ("new",)
    assert sent == [("update", ["flow"])]

    sent.clear()
    outlet.set_state({"flow": ["new", "r"]})
    # echo_update stays on for flow; the browser JSON equals the re-serialised
    # value so the stock lock check suppresses the second update
    assert sent == [("echo_update", ["flow"])]
    assert outlet.flow == ("new", "r")


def test_observer_write_during_browser_write_is_sent_once(monkeypatch):
    """Only the browser's *own* object is suppressed: an observer that reacts
    to the browser's tree by assigning a new one does so while the property
    lock is still held, and that tree must reach the frontend (#164 review).
    """
    outlet = MarkElementWidget()
    sent = capture_sends(outlet, monkeypatch)
    replacement = Node(id="root", children=[Node(id="replaced")])

    def react(change):
        if change.new is not replacement:
            outlet.value = replacement

    outlet.observe(react, "value")
    outlet.set_state({"value": browser_wire()})

    assert sent == [("update", ["value"])], (
        "the observer's tree, once; not the browser's"
    )
    assert outlet.value is replacement

    # the plain browser write is still silent
    outlet.unobserve(react, "value")
    sent.clear()
    outlet.set_state({"value": browser_wire()})
    assert sent == []
