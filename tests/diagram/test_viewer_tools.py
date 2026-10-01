# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The viewer's Fit/Center buttons reach ``fit``/``center`` on every ``Viewer``."""

from unittest import mock

import pytest

from ipyelk.diagram import SprottyViewer, Viewer


@pytest.mark.parametrize("cls", [Viewer, SprottyViewer])
@pytest.mark.parametrize(
    ("tool", "method"), [("fit_tool", "fit"), ("center_tool", "center")]
)
def test_button_click_calls_the_viewer_once(cls, tool, method):
    view = cls()
    with mock.patch.object(view, method) as spy:
        getattr(view, tool).ui.click()
    assert spy.call_count == 1


@pytest.mark.parametrize("method", ["fit", "center"])
def test_sprotty_viewer_sends_one_id_for_a_string_and_a_list_for_a_sequence(method):
    view = SprottyViewer()
    with mock.patch.object(view, "send") as send:
        getattr(view, method)("n1")
        getattr(view, method)(("n1", "n2"))
        getattr(view, method)()
    payloads = [call.args[0]["model_id"] for call in send.call_args_list]
    assert payloads == [["n1"], ["n1", "n2"], None]


def test_sprotty_viewer_default_buttons_pass_the_selection():
    view = SprottyViewer()
    view.selection.ids = ("a", "b")
    with mock.patch.object(view, "send") as send:
        view.fit_tool.ui.click()
        view.center_tool.ui.click()
    assert [c.args[0]["model_id"] for c in send.call_args_list] == [["a", "b"]] * 2
