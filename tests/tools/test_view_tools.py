# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Browser-written traits must not be echoed back to the frontends (#164)."""

import pytest

from ipyelk.elements import Label, Node
from ipyelk.pipes import MarkElementWidget
from ipyelk.tools import Hover, Selection


def capture_sends(widget, monkeypatch):
    """Record every comm message ``widget`` would send as ``(method, keys)``."""
    sent = []

    def _send(msg, buffers=None):
        sent.append((msg["method"], sorted(msg.get("state", {}))))

    monkeypatch.setattr(widget, "_send", _send)
    return sent


@pytest.mark.parametrize(
    ("cls", "name"),
    [(Selection, "ids"), (Hover, "ids"), (MarkElementWidget, "value")],
)
def test_browser_written_traits_are_tagged_echo_off(cls, name):
    widget = cls()
    assert widget.trait_metadata(name, "sync") is True
    assert widget.trait_metadata(name, "echo_update") is False


@pytest.mark.parametrize(
    ("cls", "name", "wire"),
    [
        (Selection, "ids", ["n1", "n2"]),
        (Hover, "ids", "n1"),
    ],
)
def test_browser_written_traits_do_not_echo(cls, name, wire, monkeypatch):
    widget = cls()
    sent = capture_sends(widget, monkeypatch)

    widget.set_state({name: wire})

    assert sent == []
    assert widget.trait_metadata(name, "echo_update") is False


def test_selection_write_of_current_value_is_silent(monkeypatch):
    """The browser re-sending what the kernel already holds produces no send."""
    sel = Selection(ids=("n1",))
    sent = capture_sends(sel, monkeypatch)

    sel.set_state({"ids": ["n1"]})

    assert sel.ids == ("n1",)
    assert sent == []


def test_kernel_write_of_selection_still_reaches_browser(monkeypatch):
    sel = Selection()
    sent = capture_sends(sel, monkeypatch)

    sel.ids = ("n1", "n2")

    assert sent == [("update", ["ids"])]


def test_outlet_value_write_from_browser_does_not_echo(monkeypatch):
    root = Node(id="root", children=[Node(id="a", labels=[Label(id="l", text="A")])])
    wire = root.model_dump()
    wire["children"][0]["labels"][0]["width"] = 12.5  # browser measured
    wire["$H"] = 123  # elkjs internals never round-trip through pydantic
    outlet = MarkElementWidget()
    sent = capture_sends(outlet, monkeypatch)

    outlet.set_state({"value": wire})

    assert outlet.value.children[0].labels[0].width == pytest.approx(12.5)
    assert sent == []
