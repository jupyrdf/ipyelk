# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``MarkElementWidget`` send behavior (#164)."""

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
    outlet = MarkElementWidget().sync_value()
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


def test_value_and_flow_are_not_synced_by_default(monkeypatch):
    """A mark that no browser stage reads sends nothing: not ``value``, not ``flow``."""
    mark = MarkElementWidget(value=Node(id="root"))
    assert "value" not in mark.get_state()
    assert "flow" not in mark.get_state()
    sent = capture_sends(mark, monkeypatch)

    mark.flow = ("new",)
    mark.value = Node(id="other")
    assert sent == []
    mark.set_state({"value": browser_wire(), "flow": ["r"]})
    assert mark.value.id == "other", "a browser write to an unsynced value is ignored"
    assert mark.flow == ("new",)


def test_sync_value_sends_the_value_once(monkeypatch):
    mark = MarkElementWidget(value=Node(id="root"))
    sent = capture_sends(mark, monkeypatch)
    assert mark.sync_value() is mark
    assert sent == [("update", ["value"])]
    assert mark.get_state("value")["value"]["id"] == "root"
    mark.sync_value()
    assert sent == [("update", ["value"])], "a second call sends nothing"
    mark.value = Node(id="other")
    assert sent[-1] == ("update", ["value"])
    mark.flow = ("new",)
    assert sent[-1] == ("update", ["value"]), "flow stays unsynced"


def test_observer_write_during_browser_write_is_sent_once(monkeypatch):
    """Only the browser's *own* object is suppressed: an observer that reacts
    to the browser's tree by assigning a new one does so while the property
    lock is still held, and that tree must reach the frontend (#164 review).
    """
    outlet = MarkElementWidget().sync_value()
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


def test_only_the_marks_a_browser_stage_uses_sync_value():
    """The browser reads the inlets of the text sizer and the layout, writes
    their outlets, and draws the source of the viewer. The source of the
    diagram stays in the kernel.
    """
    from ipyelk import Diagram
    from ipyelk.pipes import Pipe

    diagram = Diagram(source=MarkElementWidget(value=Node(id="root")))
    validation, sizer, visibility, elkjs = diagram.pipe.pipes
    synced = {
        "source": diagram.source,
        "validation.outlet": validation.outlet,
        "sizer.outlet": sizer.outlet,
        "visibility.outlet": visibility.outlet,
        "elkjs.outlet": elkjs.outlet,
    }
    assert {name for name, mark in synced.items() if "value" in mark.keys} == {
        "validation.outlet",
        "sizer.outlet",
        "visibility.outlet",
        "elkjs.outlet",
    }
    assert diagram.view.source is elkjs.outlet
    assert not any("flow" in mark.keys for mark in synced.values())

    kernel_only = Pipe()
    assert "value" not in kernel_only.inlet.keys
    assert "value" not in kernel_only.outlet.keys
    kernel_only.close()
    diagram.close()
