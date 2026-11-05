# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.elements import Label, Node, NodeProperties
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes import flows as F
from ipyelk.pipes.text_sizer import BrowserTextSizer, size_nested_label

LABEL_LABEL = "org.eclipse.elk.spacing.labelLabel"


def test_nested_label_width_includes_spacing_two_levels():
    """``labelLabel`` spacing is added to every sized sublabel, not only to
    sublabels without a width (``a or b + c`` parsed as ``a or (b + c)``).
    """
    inner = Label(text="inner", width=10, height=5, layoutOptions={LABEL_LABEL: 4})
    mid = Label(
        text="mid",
        width=20,
        height=7,
        labels=[inner],
        layoutOptions={LABEL_LABEL: 8},
    )
    outer = Label(text="outer", width=50, height=6, labels=[mid])

    size_nested_label(outer)

    assert mid.width == 34  # 20 + (10 + 4)
    assert outer.width == 92  # 50 + (34 + 8)
    assert mid.height == 7
    assert outer.height == 7
    assert inner.width == 10
    assert inner.height == 5


@pytest.fixture
def measured_sizer(monkeypatch):
    """Exercise the real sizer run, replacing only its browser transport."""
    calls = []

    async def browser(pipe, **kwargs):
        wire = pipe.inlet.value.model_dump(mode="json", exclude_none=True)

        def measure(el):
            if "text" in el:
                el["width"] = len(el["text"]) * 7
                el["height"] = 12
            for key in ("children", "ports", "edges", "labels"):
                for child in el.get(key, []):
                    measure(child)

        calls.append(wire)
        measure(wire)
        pipe.outlet.set_state({"value": wire})

    monkeypatch.setattr("ipyelk.pipes.text_sizer.browser_roundtrip", browser)
    label = Label(id="label", text="hidden")
    child = Node(id="child", labels=[label], properties=NodeProperties(hidden=True))
    root = Node(id="root", children=[child])
    mark = MarkElementWidget(value=root)
    mark.build_index()
    pipe = BrowserTextSizer(inlet=mark)
    pipe.outlet.share_index(mark)
    yield pipe, root, child, label, calls
    pipe.close()
    mark.close()


@pytest.mark.asyncio
async def test_initially_hidden_label_is_measured_on_reveal(measured_sizer):
    pipe, _root, child, label, calls = measured_sizer
    await pipe.run()
    assert calls[-1]["children"] == []
    child.properties.hidden = False
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert label.width == 42
    assert label.height == 12
    child.properties.hidden = True
    assert not pipe.check_dirty((F.Node.hidden,))
    child.properties.hidden = False
    assert not pipe.check_dirty((F.Node.hidden,))
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_hidden_text_edit_is_measured_on_reveal(measured_sizer):
    pipe, _root, child, label, calls = measured_sizer
    child.properties.hidden = False
    await pipe.run()
    assert label.width == 42
    child.properties.hidden = True
    assert not pipe.check_dirty((F.Node.hidden,))
    label.text = "a much longer hidden label"
    assert pipe.check_dirty((F.Text.text,))
    await pipe.run()
    assert calls[-1]["children"] == []
    assert label.width == 42
    child.properties.hidden = False
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert label.width == len(label.text) * 7


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["classes", "css", "nested", "replacement"])
async def test_reveal_checks_measurement_inputs(measured_sizer, change):
    pipe, root, child, label, _calls = measured_sizer
    child.properties.hidden = False
    await pipe.run()
    child.properties.hidden = True
    if change == "classes":
        label.properties.cssClasses = "larger"
    elif change == "css":
        pipe.style = {" .elklabel": {"font-size": "30px"}}
    elif change == "nested":
        label.labels = [Label(id="nested", text="nested")]
        pipe.inlet.build_index()
    else:
        replacement = Label(id=label.id, text=label.text)
        root.children = [Node(id=child.id, labels=[replacement])]
        pipe.inlet.build_index()
    if change != "replacement":
        # A hidden-text run measures only the remaining visible labels.
        await pipe.run()
        child.properties.hidden = False
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert not pipe.check_dirty((F.Node.hidden,))


@pytest.mark.asyncio
async def test_failed_reveal_is_not_remembered(measured_sizer, monkeypatch):
    pipe, _root, child, _label, _calls = measured_sizer
    await pipe.run()
    child.properties.hidden = False

    async def failure(_pipe, **_kwargs):
        raise RuntimeError("measurement failed")

    monkeypatch.setattr("ipyelk.pipes.text_sizer.browser_roundtrip", failure)
    assert pipe.check_dirty((F.Node.hidden,))
    with pytest.raises(RuntimeError, match="measurement failed"):
        await pipe.run()
    assert pipe.check_dirty((F.Node.hidden,))


@pytest.mark.asyncio
async def test_replaced_root_does_not_retain_old_measurements(measured_sizer):
    pipe, _root, child, label, _calls = measured_sizer
    child.properties.hidden = False
    await pipe.run()
    replacement = Node(
        id="root",
        children=[Node(id="child", labels=[Label(id=label.id, text=label.text)])],
    )
    pipe.inlet.value = replacement
    pipe.inlet.build_index()
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert not pipe.check_dirty((F.Node.hidden,))
    assert len(pipe._measured) == 1


@pytest.mark.asyncio
async def test_revealed_nested_label_is_measured(measured_sizer):
    pipe, _root, child, label, calls = measured_sizer
    nested = Label(id="nested", text="nested")
    label.labels = [nested]
    label.properties.hidden = True
    child.properties.hidden = False
    pipe.inlet.build_index()
    await pipe.run()
    label.properties.hidden = False
    assert pipe.check_dirty((F.Text.hidden,))
    await pipe.run()
    assert nested.width == 42
    assert label.width == 42
    assert not pipe.check_dirty((F.Text.hidden,))
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_hidden_edge_labels_do_not_trigger_sizing(measured_sizer):
    pipe, root, child, _label, _calls = measured_sizer
    child.labels = []
    edge = root.add_edge(child, root)
    edge.labels = [Label(text="edge to hidden child")]
    pipe.inlet.build_index()
    await pipe.run()
    assert not pipe.check_dirty((F.Node.hidden,))
    child.properties.hidden = False
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert edge.labels[0].width > 0
    child.properties.hidden = True
    assert not pipe.check_dirty((F.Node.hidden,))


@pytest.mark.asyncio
async def test_reveal_syncs_in_place_changes_before_browser_sizing(
    measured_sizer, monkeypatch
):
    """The browser reads transmitted widget state, not the current Python tree."""
    import copy

    pipe, _root, child, label, _calls = measured_sizer
    frontend = pipe.inlet.get_state("value")["value"]
    synced = []

    def send_state(key=None, **_kwargs):
        nonlocal frontend
        synced.append(key)
        frontend = pipe.inlet.get_state("value")["value"]

    async def retained_browser(pipe, **_kwargs):
        wire = copy.deepcopy(frontend)
        for node in wire["children"]:
            for text in node["labels"]:
                text["width"] = len(text["text"]) * 7
                text["height"] = 12
        pipe.outlet.set_state({"value": wire})

    monkeypatch.setattr(pipe.inlet, "send_state", send_state)
    monkeypatch.setattr("ipyelk.pipes.text_sizer.browser_roundtrip", retained_browser)
    await pipe.run()
    child.properties.hidden = False
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert label.width == 42
    assert synced == ["value", "value"]
    child.properties.hidden = True
    assert not pipe.check_dirty((F.Node.hidden,))
    child.properties.hidden = False
    assert not pipe.check_dirty((F.Node.hidden,))
    assert synced == ["value", "value"]

    child.properties.hidden = True
    label.text = "changed while hidden"
    edited_text = label.text
    assert pipe.check_dirty((F.Text.text,))
    await pipe.run()
    assert label.text == edited_text
    child.properties.hidden = False
    assert pipe.check_dirty((F.Node.hidden,))
    await pipe.run()
    assert label.width == len(edited_text) * 7
    assert synced == ["value"] * 4
