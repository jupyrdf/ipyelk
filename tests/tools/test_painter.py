# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Painter``: temporary, view-only CSS classes keyed by element id."""

import warnings

import pytest
import traitlets as T

from ipyelk.diagram import Viewer
from ipyelk.elements import Node
from ipyelk.exceptions import DeprecatedAPIError, NotFoundError
from ipyelk.pipes import Pipe
from ipyelk.tools import Painter


def _painter() -> Painter:
    pipe = Pipe()
    pipe.inlet.value = Node(id="root", children=[Node(id="n1"), Node(id="n2")])
    return Painter(tee=pipe)


def test_defaults_and_state_only():
    painter = Painter()
    assert painter.styles == {}
    assert painter.painted_ids == ()
    assert painter.ui is None
    assert painter.reports == ()
    assert painter.trait_metadata("styles", "sync") is True
    with pytest.raises(NotImplementedError):
        painter.trigger()  # no run(): nothing to schedule, no re-layout


def test_paint_unions_per_id_preserving_order_and_notifies_once_per_call():
    painter = Painter()
    seen = []
    painter.observe(lambda change: seen.append(dict(change.new)), "styles")
    painter.paint(["n1", "n2"], "hl", "warn")
    painter.paint("n1", "warn", "extra")  # a str is one id, not its characters
    assert painter.styles == {"n1": ("hl", "warn", "extra"), "n2": ("hl", "warn")}
    assert painter.painted_ids == ("n1", "n2")
    assert len(seen) == 2  # each call assigns one new dict


def test_unpaint_classes_then_ids():
    painter = Painter()
    painter.paint(["n1", "n2"], "hl", "warn")
    painter.unpaint(["n1", "n2"], "warn")
    assert painter.styles == {"n1": ("hl",), "n2": ("hl",)}
    painter.unpaint("n1", "hl")  # the last class goes: so does the id
    assert painter.styles == {"n2": ("hl",)}
    painter.unpaint("n2")  # no classes: drop the id entirely
    painter.unpaint("never-painted", "hl")  # ignored
    assert painter.styles == {}


def test_clear_drops_everything():
    painter = Painter()
    painter.paint("n1", "hl")
    painter.clear()
    assert painter.styles == {}
    assert painter.painted_ids == ()


def test_elements_are_accepted_and_stored_as_ids():
    painter = _painter()
    n1, n2 = painter.tee.inlet.value.children
    painter.paint(n1, "hl")
    painter.paint([n2, "n1"], "warn")
    assert painter.styles == {"n1": ("hl", "warn"), "n2": ("warn",)}
    with pytest.raises(ValueError, match="no id"):
        painter.paint(Node(), "hl")  # an unregistered element has no id yet


def test_browser_update_arrives_as_lists_and_is_stored_as_tuples():
    painter = Painter()
    painter.set_state({"styles": {"n1": ["hl", "warn"]}})
    assert painter.styles == {"n1": ("hl", "warn")}
    painter.styles = {"n2": ["a"]}
    assert painter.styles == {"n2": ("a",)}
    with pytest.raises(T.TraitError):
        painter.styles = {"n1": "hl"}  # one class is still a tuple, not a str


def test_elements_strict_and_missing_ids_mirror_selection():
    painter = _painter()
    painter.paint(["n1", "gone", "n2"], "hl")  # ids are never filtered on assignment
    assert painter.painted_ids == ("n1", "gone", "n2")
    with pytest.raises(NotFoundError, match="gone"):
        list(painter.elements())
    assert [el.id for el in painter.elements(strict=False)] == ["n1", "n2"]
    assert painter.missing_ids() == ("gone",)
    unattached = Painter()
    unattached.paint("n1", "hl")
    with pytest.raises(ValueError, match="not attached to a pipe"):
        list(unattached.elements())
    assert Painter(tee=Pipe(), styles={"n1": ("hl",)}).missing_ids() == ("n1",)


def test_painting_never_touches_the_model():
    painter = _painter()
    n1 = painter.tee.inlet.value.children[0]
    before = n1.model_dump()
    painter.paint(n1, "hl")
    assert n1.model_dump() == before
    assert "hl" not in (n1.properties.cssClasses or "")


def test_viewer_owns_a_live_painter_bound_by_the_diagram():
    from ipyelk import Diagram

    viewer = Viewer()
    assert isinstance(viewer.painter, Painter)
    assert viewer.trait_metadata("painter", "sync") is True
    diagram = Diagram()
    # a default tool (no UI, so not in the toolbar): elements() resolves on the pipe
    assert diagram.view.painter in diagram.tools
    assert diagram.view.painter.tee is diagram.pipe
    assert diagram.view.painter not in [t.ui for t in diagram.tools if t.ui is not None]


@pytest.mark.parametrize("name", ["cssClasses", "marks", "name"])
def test_removed_names_are_hard_errors_throughout_3x(name):
    painter = Painter()
    painter.paint("n1", "hl")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a warning must not pass for compliance
        with pytest.raises(DeprecatedAPIError, match=r"painter\.") as info:
            getattr(painter, name)
        assert "3.x" in str(info.value)
        with pytest.raises(DeprecatedAPIError, match=r"painter\."):
            setattr(painter, name, "x")
        with pytest.raises(DeprecatedAPIError, match=r"painter\."):
            Painter(**{name: "x"})
    assert painter.styles == {"n1": ("hl",)}  # rejected writes had no side effect
    assert name not in Painter.class_trait_names()  # nothing synced under the old name
    assert getattr(Painter, name).__doc__.startswith("Removed in 3.0")  # docs-safe
