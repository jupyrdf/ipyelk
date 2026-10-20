# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Viewer.fit_on_first_layout``: each view fits itself, in the browser (gh-245)."""

from unittest import mock

import pytest
import traitlets as T

from ipyelk import Diagram
from ipyelk.diagram import SprottyViewer, Viewer

TRAITS = {"fit_on_first_layout": False, "fit_padding": 0.0, "fit_max_zoom": None}


@pytest.mark.parametrize("cls", [Viewer, SprottyViewer])
def test_opt_in_traits_sync_with_defaults(cls):
    view = cls()
    for name, default in TRAITS.items():
        assert getattr(view, name) == default
        assert view.trait_metadata(name, "sync") is True
    state = view.get_state()
    assert {name: state[name] for name in TRAITS} == TRAITS


def test_diagram_view_takes_the_traits():
    diagram = Diagram(view=SprottyViewer(fit_on_first_layout=True, fit_padding=10))
    assert diagram.view.fit_on_first_layout is True
    assert diagram.view.fit_padding == 10


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("fit_padding", -1),
        ("fit_padding", float("inf")),
        ("fit_padding", float("nan")),
        ("fit_max_zoom", 0),
        ("fit_max_zoom", -2),
        ("fit_max_zoom", float("inf")),
        ("fit_max_zoom", float("nan")),
    ],
)
def test_rejects_padding_and_zoom_that_cannot_frame(name, value):
    with pytest.raises(T.TraitError):
        SprottyViewer(**{name: value})


def test_fit_defaults_to_the_viewer_padding_and_max_zoom():
    view = SprottyViewer(fit_padding=12, fit_max_zoom=2)
    with mock.patch.object(view, "send") as send:
        view.fit()
        view.fit(padding=0, max_zoom=5)  # explicit arguments still win
        view.fit_tool.ui.click()
    sent = [(c.args[0]["padding"], c.args[0]["max_zoom"]) for c in send.call_args_list]
    assert sent == [(12, 2), (0, 5), (12, 2)]


def test_fit_without_viewer_defaults_is_unpadded_and_unlimited():
    view = SprottyViewer()
    with mock.patch.object(view, "send") as send:
        view.fit()
    content = send.call_args.args[0]
    assert (content["padding"], content["max_zoom"]) == (0.0, None)
