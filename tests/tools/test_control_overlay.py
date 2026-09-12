# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Viewer.control_overlay`` is opt-in (issue #156, item 8)."""

from __future__ import annotations

import importlib
import sys
import warnings

import ipywidgets as W
import pytest

from ipyelk.diagram import SprottyViewer, Viewer
from ipyelk.exceptions import DeprecatedAPIError
from ipyelk.tools import ControlOverlay


@pytest.mark.parametrize("viewer_class", [Viewer, SprottyViewer])
def test_control_overlay_defaults_to_none(viewer_class: type[Viewer]) -> None:
    """No overlay widget is allocated unless the user provides one."""
    assert viewer_class().control_overlay is None


def test_control_overlay_accepts_explicit_overlay() -> None:
    """A user-provided overlay is kept, with its children intact."""
    button = W.Button(description="edit")
    viewer = Viewer(control_overlay=ControlOverlay(children=[button]))
    assert isinstance(viewer.control_overlay, ControlOverlay)
    assert viewer.control_overlay.children == (button,)
    # the browser reads ``children`` off the synced VBox: it is a synced trait
    assert ControlOverlay.class_traits()["children"].metadata.get("sync")


def test_control_overlay_syncs_as_widget_reference() -> None:
    """``None`` and an overlay both serialize through ``widget_serialization``."""
    assert Viewer().get_state(key="control_overlay") == {"control_overlay": None}
    overlay = ControlOverlay()
    state = Viewer(control_overlay=overlay).get_state(key="control_overlay")
    assert state == {"control_overlay": f"IPY_MODEL_{overlay.model_id}"}


def test_control_overlay_module_renamed_without_alias() -> None:
    """``ipyelk.tools.control_overlay`` is the only import path in 3.0."""
    module = importlib.import_module("ipyelk.tools.control_overlay")
    assert module.ControlOverlay is ControlOverlay


def test_old_contol_overlay_module_is_an_error_only_guard() -> None:
    """The misspelled module raises ``DeprecatedAPIError`` (3.x) and forwards nothing."""
    sys.modules.pop("ipyelk.tools.contol_overlay", None)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a warning must not pass for compliance
        with pytest.raises(DeprecatedAPIError, match=r"ipyelk\.tools\.control_overlay"):
            importlib.import_module("ipyelk.tools.contol_overlay")
        assert "ipyelk.tools.contol_overlay" not in sys.modules
        with pytest.raises(DeprecatedAPIError, match=r"3\.x"):
            from ipyelk.tools import contol_overlay  # ruff: ignore[unused-import]
    import ipyelk.tools  # the package itself is unaffected

    assert ipyelk.tools.ControlOverlay is ControlOverlay
