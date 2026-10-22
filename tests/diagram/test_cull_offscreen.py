# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Viewer.cull_offscreen``: a view renders only what touches its canvas (gh-170)."""

import pytest

from ipyelk import Diagram
from ipyelk.diagram import SprottyViewer, Viewer


@pytest.mark.parametrize("cls", [Viewer, SprottyViewer])
def test_culling_is_off_by_default_and_synced(cls):
    view = cls()
    assert view.cull_offscreen is False
    assert view.trait_metadata("cull_offscreen", "sync") is True
    assert view.get_state()["cull_offscreen"] is False


def test_culling_can_be_turned_on():
    diagram = Diagram(view=SprottyViewer(cull_offscreen=True))
    assert diagram.view.cull_offscreen is True
    assert diagram.view.get_state()["cull_offscreen"] is True
    diagram.view.cull_offscreen = False
    assert diagram.view.get_state()["cull_offscreen"] is False
