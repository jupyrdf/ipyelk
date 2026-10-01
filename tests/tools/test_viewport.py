# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Viewer.viewport`` (browser-written snapshot) and ``set_viewport`` (command)."""

import warnings

import pytest
import traitlets as T

import ipyelk.tools
from ipyelk.diagram import SprottyViewer, Viewer
from ipyelk.exceptions import DeprecatedAPIError, DeprecatedImportError
from ipyelk.tools import Viewport

FIELDS = ("view_id", "origin", "zoom", "canvas_size", "viewed_ids")
REPORT = {
    "view_id": "view-1",
    "origin": [10.0, -20.5],
    "zoom": 1.5,
    "canvas_size": [640, 480],
    "viewed_ids": ["n1", "n2"],
}


def test_defaults_are_none_and_state_only():
    viewport = Viewport()
    assert all(getattr(viewport, name) is None for name in FIELDS)
    assert viewport.ui is None
    with pytest.raises(NotImplementedError):  # no run(): a state-only tool
        viewport.trigger()
    assert all(viewport.trait_metadata(name, "sync") is True for name in FIELDS)


@pytest.mark.parametrize("name", FIELDS)
def test_reports_are_synced_but_never_echoed(name):
    # the browser is the only writer: an echo (ipywidgets 8.1 default) would send
    # every report, viewed_ids included, back to every connected frontend
    assert Viewport().trait_metadata(name, "echo_update") is False


def test_browser_report_is_not_echoed_back(monkeypatch):
    import ipywidgets.widgets.widget as widget_module

    monkeypatch.setattr(widget_module, "JUPYTER_WIDGETS_ECHO", True)
    viewport = Viewport()
    sent = []
    monkeypatch.setattr(viewport, "_send", lambda msg, _buffers=None: sent.append(msg))
    viewport.set_state({**REPORT, "viewed_ids": [f"n{i}" for i in range(1000)]})
    assert len(viewport.viewed_ids) == 1000
    assert [msg["method"] for msg in sent] == []  # no ``echo_update``


@pytest.mark.parametrize("name", FIELDS)
def test_kernel_assignment_is_rejected(name):
    viewport = Viewport()
    with pytest.raises(T.TraitError, match="read-only"):
        setattr(viewport, name, REPORT[name])
    assert getattr(viewport, name) is None


def test_browser_report_applies_all_fields_in_one_notification():
    """``set_state`` is how a comm update lands; observers see the whole snapshot."""
    viewport = Viewport()
    seen = []
    viewport.observe(
        lambda change: seen.append((
            change.name,
            {name: getattr(viewport, name) for name in FIELDS},
        )),
        list(FIELDS),
    )
    viewport.set_state(dict(REPORT))
    assert viewport.view_id == "view-1"
    assert viewport.origin == (10.0, -20.5)
    assert viewport.zoom == pytest.approx(1.5)
    assert viewport.canvas_size == (640.0, 480.0)
    assert viewport.viewed_ids == ("n1", "n2")
    # one notification per field, each already seeing the complete snapshot
    assert sorted(name for name, _ in seen) == sorted(FIELDS)
    expected = {
        "view_id": "view-1",
        "origin": (10.0, -20.5),
        "zoom": 1.5,
        "canvas_size": (640.0, 480.0),
        "viewed_ids": ("n1", "n2"),
    }
    assert all(snapshot == expected for _, snapshot in seen)


def test_viewer_owns_a_viewport_that_is_not_a_default_tool():
    from ipyelk import Diagram

    viewer = Viewer()
    assert isinstance(viewer.viewport, Viewport)
    assert viewer.trait_metadata("viewport", "sync") is True
    diagram = Diagram()
    assert diagram.view.viewport not in diagram.tools


def test_set_viewport_sends_one_documented_message():
    viewer = SprottyViewer()
    sent = []
    viewer.send = lambda content, _buffers=None: sent.append(content)
    viewer.set_viewport(origin=(1, 2), zoom=2, animate=False, view_id="view-1")
    assert sent == [
        {
            "action": "viewport",
            "origin": [1.0, 2.0],
            "zoom": 2.0,
            "animate": False,
            "view_id": "view-1",
        }
    ]
    sent.clear()
    viewer.set_viewport()  # keep origin and zoom, every view, animated
    assert sent == [
        {
            "action": "viewport",
            "origin": None,
            "zoom": None,
            "animate": True,
            "view_id": None,
        }
    ]
    assert viewer.viewport.zoom is None  # a command never writes the reported state


@pytest.mark.parametrize(
    ("name", "replacement"),
    [("zoom", "set_viewport"), ("pan", "set_viewport"), ("viewed", "viewed_ids")],
)
@pytest.mark.parametrize("cls", [Viewer, SprottyViewer])
def test_viewer_zoom_pan_viewed_are_hard_errors_throughout_3x(cls, name, replacement):
    viewer = cls()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a warning must not pass for compliance
        with pytest.raises(DeprecatedAPIError, match=replacement) as info:
            getattr(viewer, name)
        message = str(info.value)
        assert "3.x" in message
        assert "viewer.viewport" in message
        with pytest.raises(DeprecatedAPIError, match=replacement):
            setattr(viewer, name, None)
        with pytest.raises(DeprecatedAPIError, match=replacement):
            cls(**{name: None})
    assert viewer.viewport.zoom is None  # rejected writes had no side effect
    assert name not in cls.class_trait_names()  # nothing synced under the old name
    assert getattr(cls, name).__doc__.startswith("Removed in 3.0")  # docs-safe


@pytest.mark.parametrize("name", ["Zoom", "Pan"])
def test_zoom_and_pan_classes_are_hard_errors_throughout_3x(name):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # `from ipyelk.tools import Zoom` resolves through the same module __getattr__
        with pytest.raises(DeprecatedImportError, match=r"viewer\.viewport") as info:
            getattr(ipyelk.tools, name)
        assert "3.x" in str(info.value)
        assert "set_viewport" in str(info.value)
    assert name not in ipyelk.tools.__all__
    assert name not in dir(ipyelk.tools)
    assert not hasattr(ipyelk.tools, "NoSuchTool")  # unknown names stay AttributeError
