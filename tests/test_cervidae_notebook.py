"""Regression checks using the actual Cervidae notebook construction code."""

import asyncio
import json
import re
from pathlib import Path

import pytest


@pytest.fixture
def scope(monkeypatch):
    examples = Path(__file__).resolve().parents[1] / "examples"
    monkeypatch.chdir(examples)
    notebook = json.loads(
        (examples / "16_Cervidae_Tree.ipynb").read_text(encoding="utf-8")
    )
    scope = {"__name__": "cervidae_test"}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            # Execute trusted repository notebook cells to cover their real wiring.
            exec(compile("".join(cell["source"]), cell["id"], "exec"), scope)  # ruff: ignore[exec-builtin]
    return scope


def test_taxonomy_styles_anchors_and_collapse(scope):
    attributes = scope["node_attributes"]
    text = attributes("Odocoileini")
    assert 'stroke="none"' in text["properties"]["shape"]["use"]
    assert (
        "INSIDE"
        in text["labels"][0]["layoutOptions"]["org.eclipse.elk.nodeLabels.placement"]
    )
    photo = attributes(next(iter(scope["images"])))
    assert (photo["width"], photo["height"]) == (90, 64)
    assert (
        photo["labels"][0]["layoutOptions"]["org.eclipse.elk.nodeLabels.placement"]
        == "H_RIGHT V_CENTER OUTSIDE"
    )
    for node in (text, photo):
        for port, x in zip(node["ports"], (0, node["width"]), strict=True):
            assert port.width == 0
            assert port.height == 0
            assert port.x == x
            assert port.y == pytest.approx(node["height"] / 2)
            assert port.properties.key == port.id
    graph = scope["graph"]
    for source, target, edge in graph.edges(data=True):
        assert edge["sourcePort"] == f"{source}.out"
        assert edge["targetPort"] == f"{target}.in"
    # Check loaded endpoints too: mismatched keys create extra default 5px ports.
    root = scope["diagram_source"].value
    for node in root.children:
        assert [port.id for port in node.ports] == [f"{node.id}.in", f"{node.id}.out"]
    for edge in root.edges:
        assert edge.source.id == f"{edge.source.get_parent().id}.out"
        assert edge.target.id == f"{edge.target.get_parent().id}.in"
    collapse = scope["collapse"]
    collapse.selection.ids = ("Odocoileini",)
    related = collapse.get_related(
        collapse.selection.get_index().from_id("Odocoileini")
    )
    assert related
    asyncio.run(collapse.run())
    assert all(node.properties.hidden for node in related)
    asyncio.run(collapse.run())
    assert not any(node.properties.hidden for node in related)


def test_species_card_status_and_range(scope):
    render_card = scope["species_details"]
    record = dict(next(iter(scope["records_by_id"].values())))
    record.update(status="EN", population="1,000-1,500")
    card = render_card(record)
    assert "Endangered. Reported population: 1,000-1,500" in card
    assert re.search(r"cervidae-title-row.*?<h3>.*?</h3>\s*<span", card, re.DOTALL)
    assert "cervidae-population" not in card
    record["population"] = "Unknown"
    assert "Population not reported in this snapshot." in render_card(record)
    for identifier in scope["range_images"]:
        card = render_card(scope["records_by_id"][identifier])
        range_row = re.search(r"<dt>Range</dt><dd>(.*?)</dd>", card, re.DOTALL)
        assert range_row is not None
        assert "cervidae-range-map" in range_row[1]
        assert card.count("cervidae-range-map") == 1


def test_card_child_selection(scope):
    # Follow actual button callbacks from a tribe to a genus and then a species.
    graph = scope["graph"]
    scope["select_taxon"]("Odocoileini")
    group = scope["details"].children[0]
    genus = next(graph.successors("Odocoileini"))
    group.children[1].children[0].children[0].click()
    assert scope["diagram"].view.selection.ids == (genus,)
    species_id = next(graph.successors(genus))
    index = scope["diagram"].view.selection.get_index()
    index.from_id(species_id).properties.hidden = True
    genus_card = scope["details"].children[0]
    row = genus_card.children[1]
    assert "cervidae-status" in row.children[0].value
    assert row.children[1].children[0].layout.margin == "0"
    row.children[1].children[0].click()
    assert scope["diagram"].view.selection.ids == (species_id,)
    assert not index.from_id(species_id).properties.hidden
    assert (
        scope["records_by_id"][species_id]["common_name"]
        in scope["details"].children[0].value
    )


def test_parent_card_collapse_button(scope, monkeypatch):
    scope["select_taxon"]("Odocoileini")
    refresh_reports = []
    monkeypatch.setattr(
        scope["diagram"],
        "refresh",
        lambda: refresh_reports.append(scope["diagram"].pipe.inlet.flow),
    )
    card = scope["details"].children[0]
    button = card.children[0].children[1]
    index = scope["diagram"].view.selection.get_index()
    related = scope["collapse"].get_related(index.from_id("Odocoileini"))
    assert button.tooltip == "Collapse descendants of Odocoileini"
    button.click()
    assert all(node.properties.hidden for node in related)
    assert scope["F"].Node.hidden in refresh_reports[-1]
    assert button.description == "+"
    button.click()
    assert not any(node.properties.hidden for node in related)
    assert button.tooltip == "Collapse descendants of Odocoileini"
    assert scope["diagram"].view.selection.ids == ("Odocoileini",)
    assert scope["collapse"] not in scope["diagram"].tools
    assert len(refresh_reports) == 2


def test_junction_selection_and_visibility(scope):
    index = scope["diagram"].view.selection.get_index()
    identifier = scope["toggle_ids"]["Odocoileini"]
    control = index.from_id(identifier)
    assert control.labels == []
    scope["diagram"].view.selection.ids = (identifier,)
    assert "M 12 7 V 17" in control.properties.shape.use
    assert not control.properties.hidden
    assert scope["diagram"].view.selection.ids == ("Odocoileini",)
    outgoing = [
        edge
        for _, edge in index.elements.edges()
        if edge.source.get_parent() is control
    ]
    assert all(edge.properties.hidden for edge in outgoing)
    scope["diagram"].view.selection.ids = (identifier,)
    assert "M 12 7 V 17" not in control.properties.shape.use
    assert not any(edge.properties.hidden for edge in outgoing)
    assert len(scope["render_graph"]) == len(scope["graph"]) + len(scope["toggle_ids"])


def test_photos_only_on_species(scope):
    assert set(scope["images"]) == set(scope["records_by_id"])
    for name in scope["toggle_ids"]:
        assert (
            scope["node_attributes"](name)["properties"]["shape"]["type"]
            != "node:image"
        )


def test_card_prefers_wikipedia_photo(scope):
    assert scope["wikipedia_photos"]
    for identifier, photo in scope["wikipedia_photos"].items():
        assert scope["species_images"][identifier] == scope["card_overrides"].get(
            identifier, photo
        )
        assert not photo[0].startswith("images/user/")
    for identifier, photo in scope["images"].items():
        assert photo[0].startswith("images/user/")
        if (
            identifier not in scope["wikipedia_photos"]
            and identifier not in scope["card_overrides"]
        ):
            assert scope["species_images"][identifier] == photo
    for identifier, photo in scope["card_overrides"].items():
        assert scope["species_images"][identifier] == photo
        assert scope["images"][identifier] != photo
