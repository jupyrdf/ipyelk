# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Native Pydantic serialization of graph references and polymorphic models."""

import json
from uuid import UUID

import pytest
from ipywidgets import HTML
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from ipyelk.contrib.library.activity import ActivityDiagram
from ipyelk.contrib.library.block import BlockDiagram
from ipyelk.elements import (
    Compartment,
    Edge,
    ElementIndex,
    EndpointSymbol,
    Label,
    Mark,
    Node,
    NodeProperties,
    Partition,
    Port,
    Record,
    Registry,
    SymbolSpec,
    convert_elkjson,
    exclude_layout,
    shapes,
)
from ipyelk.elements.elements import (
    BaseProperties,
    EdgeProperties,
    LabelProperties,
    PortProperties,
)
from ipyelk.elements.serialization import to_json


class TaggedNode(Node):
    tag: str = "custom"
    secret: str = Field("private", exclude=True)


def test_nested_graph_exports_and_roundtrip():
    """Native Python, JSON, and TypeAdapter exports preserve the same graph."""
    label = Label(id="label", text="visible")
    child = TaggedNode(
        id="child",
        labels=[label, Label(id="hidden-label", properties={"hidden": True})],
    )
    port = child.add_port(Port(id="port"))
    root = Node(
        id="root", children=[child, Node(id="hidden", properties={"hidden": True})]
    )
    edge = root.add_edge(port, root)
    edge.id = "edge"
    root.edges.append(
        Edge(id="hidden-edge", source=child, target=root, properties={"hidden": True})
    )
    child.add_port(Port(id="hidden-port", properties={"hidden": True}))

    data = root.model_dump(exclude_none=True)
    assert json.loads(root.model_dump_json(exclude_none=True)) == data
    assert TypeAdapter(Node).dump_python(root, exclude_none=True) == data
    assert json.loads(TypeAdapter(Node).dump_json(root, exclude_none=True)) == data
    assert to_json(root, None) == data
    assert [n["id"] for n in data["children"]] == ["child"]
    nested = data["children"][0]
    assert nested["tag"] == "custom"
    assert "secret" not in nested
    assert "metadata" not in nested
    assert [p["id"] for p in nested["ports"]] == ["port"]
    assert [item["text"] for item in nested["labels"]] == ["visible"]
    assert len(data["edges"]) == 1
    assert data["edges"][0]["sources"] == ["port"]
    assert data["edges"][0]["targets"] == ["root"]
    assert "source" not in data["edges"][0]
    assert "target" not in data["edges"][0]

    restored = convert_elkjson(data)
    assert restored.children[0].get_parent() is restored
    assert restored.children[0].ports[0].get_parent() is restored.children[0]
    assert restored.edges[0].source is restored.children[0].ports[0]
    assert restored.edges[0].target is restored
    assert edge.source is port
    assert child.labels[0] is label
    index = ElementIndex.from_els(root)
    assert index["child"] is child
    assert index.model_dump()["elements"]["child"]["tag"] == "custom"


@pytest.mark.parametrize(
    ("shape", "dimensions"),
    [
        (shapes.Circle(radius=6), {"x": 6, "y": 6, "width": 12, "height": 12}),
        (shapes.Ellipse(rx=4, ry=3), {"width": 8, "height": 6}),
        (shapes.Ellipse(rx=4, ry=3, width=20), {"width": 20, "height": 6}),
    ],
)
def test_nested_shape_dimensions(shape, dimensions):
    """Derived geometry is exported without mutating the shape or node."""
    before = (shape.x, shape.y, shape.width, shape.height)
    node = Node(id="node", properties=NodeProperties(shape=shape))
    data = json.loads(node.model_dump_json(exclude_none=True))
    assert data["width"] == dimensions["width"]
    assert data["height"] == dimensions["height"]
    exported = data["properties"]["shape"]
    for key, value in dimensions.items():
        assert exported[key] == value
    assert not {"radius", "rx", "ry"} & exported.keys()
    assert (shape.x, shape.y, shape.width, shape.height) == before
    assert node.width is None
    assert node.model_dump(include={"id"}) == {"id": "node"}
    assert shape.model_dump(include={"type"}) == {"type": shape.type}


def test_nested_include_exclude():
    """Nested field selection reaches serializers without leaking excluded fields."""
    node = Node(id="root", children=[TaggedNode(id="child")])
    include = {"children": {0: {"id", "tag"}}}
    assert node.model_dump(include=include) == {
        "children": [{"id": "child", "tag": "custom"}]
    }
    exclude = {"children": {0: {"tag"}}, "width": True, "id": True}
    data = node.model_dump(exclude=exclude)
    assert "id" not in data
    assert "width" not in data
    assert "tag" not in data["children"][0]
    assert exclude == {"children": {0: {"tag"}}, "width": True, "id": True}


def test_registry_mark_and_symbol_subclasses():
    """Registry ids and endpoint-specific symbol fields survive nested exports."""
    node = TaggedNode()
    registry = Registry()
    mark = Mark(element=node, context=registry)
    data = json.loads(mark.model_dump_json(exclude_none=True))
    assert data["id"] == mark.get_id()
    assert data["tag"] == "custom"
    assert Registry.get_context(error_if_none=False) is None
    assert mark.model_dump(include={"id"}) == {"id": data["id"]}
    spec = SymbolSpec().add(
        EndpointSymbol(identifier="arrow", element=node, path_offset=shapes.Point(2, 3))
    )
    with registry:
        symbol = json.loads(spec.model_dump_json(exclude_none=True))["library"]["arrow"]
    assert symbol["path_offset"] == {"x": 2, "y": 3}
    assert symbol["element"]["tag"] == "custom"
    assert symbol["element"]["id"] == data["id"]


def test_widget_shape():
    """An embedded widget exports only its comm id, including in JSON mode."""
    widget = HTML(value="hello")
    try:
        shape = shapes.Widget(widget=widget)
        node = Node(properties={"shape": shape})
        exported = json.loads(node.model_dump_json(exclude_none=True))["properties"][
            "shape"
        ]
        assert exported["use"] == widget.model_id
        assert "widget" not in exported
        assert shape.model_dump(exclude={"use"}).get("use") is None
    finally:
        widget.close()


@pytest.mark.parametrize(
    ("properties", "shape_cls"),
    [
        (BaseProperties, shapes.BaseShape),
        (NodeProperties, shapes.NodeShape),
        (EdgeProperties, shapes.EdgeShape),
        (LabelProperties, shapes.LabelShape),
        (PortProperties, shapes.PortShape),
    ],
)
def test_lazy_shape_and_assignment_validation(properties, shape_cls):
    """Optional shapes remain lazy and assignment uses native validation."""
    value = properties()
    assert value.shape is None
    assert isinstance(value.get_shape(), shape_cls)
    assert value.get_shape() is value.shape
    with pytest.raises(ValidationError):
        value.hidden = "not a boolean"


def test_label_tooltip_round_trips():
    """``tooltip`` reaches the browser (``exclude_none`` drops it when unset)."""
    widget = HTML()
    try:
        bare = Node(id="root", labels=[Label(id="l", text="short")])
        assert "tooltip" not in to_json(bare, widget)["labels"][0]["properties"]

        root = Node(
            id="root",
            labels=[
                Label(
                    id="l",
                    text="short...",
                    properties=LabelProperties(tooltip="the full untruncated text"),
                )
            ],
        )
        data = to_json(root, widget)
        assert data["labels"][0]["properties"]["tooltip"] == "the full untruncated text"
        restored = convert_elkjson(json.loads(json.dumps(data)))
        assert restored.labels[0].properties.tooltip == "the full untruncated text"
    finally:
        widget.close()


def test_label_separator_round_trips():
    """``separator`` is opt-in: absent unless set, ``True`` reaches the browser."""
    widget = HTML()
    try:
        bare = Node(id="root", labels=[Label(id="l", text="plain")])
        assert "separator" not in to_json(bare, widget)["labels"][0]["properties"]

        root = Node(
            id="root",
            labels=[
                Label(
                    id="l",
                    text="header",
                    properties=LabelProperties(separator=True, separatorGap=2.5),
                )
            ],
        )
        data = to_json(root, widget)
        assert data["labels"][0]["properties"]["separator"] is True
        assert data["labels"][0]["properties"]["separatorGap"] == pytest.approx(2.5)
        restored = convert_elkjson(json.loads(json.dumps(data)))
        assert restored.labels[0].properties.separator is True
        assert restored.labels[0].properties.separatorGap == pytest.approx(2.5)
        with pytest.raises(ValidationError):
            LabelProperties(separator="not a boolean")
        with pytest.raises(ValidationError):
            LabelProperties(separatorGap=-1)
    finally:
        widget.close()


def test_native_validation():
    assert issubclass(Node, BaseModel)
    node = Node.model_validate_json('{"id":"root","children":[{"id":"child"}]}')
    assert node.children[0].get_parent() is node
    assert Node.model_validate(node) is node
    assert Node.model_json_schema()["$defs"]["Node"]["properties"]["children"]
    schema = Node.model_json_schema(mode="serialization")["$defs"]
    assert "children" in schema["Node"]["properties"]
    assert "metadata" not in schema["Node"]["properties"]
    assert "sources" in schema["Edge"]["properties"]
    assert "source" not in schema["Edge"]["properties"]
    with pytest.raises(ValidationError):
        node.width = "invalid"
    with pytest.raises(ValidationError):
        shapes.NodeShape(type="unknown")
    assert shapes.Comment(use=15).use == "15"
    comment = shapes.Comment()
    comment.use = 20
    assert comment.use == "20"
    with pytest.raises(ValidationError):
        shapes.Comment(use=None)
    with pytest.raises(ValidationError):
        Edge(source=node)


def test_json_compatible_widget_payload():
    """Widget transport uses JSON mode for native types in custom models."""

    class AnnotatedNode(Node):
        reference: UUID

    node = AnnotatedNode(reference=UUID(int=1))
    assert node.model_dump()["reference"] == UUID(int=1)
    assert to_json(node, None)["reference"] == str(UUID(int=1))


def test_contributed_models_and_layout_exclusion():
    """Library defaults and record layout rules work when nested under Node."""
    compartment = Compartment().make_labels(headings=["Heading"], content=["Item"])
    record = Record(children=[compartment])
    root = Node(children=[record, BlockDiagram(), ActivityDiagram(), Partition()])
    children = json.loads(root.model_dump_json())["children"]
    assert children[0]["children"][0]["layoutOptions"]
    assert "min_height" not in children[0]
    assert "bullet_shape" not in children[0]["children"][0]
    for child in children[1:]:
        assert not {"symbols", "style", "default_edge"} & child.keys()
    edge = Edge(
        source=root, target=record, sections=[{"startPoint": {}, "endPoint": {}}]
    )
    with exclude_layout:
        assert edge.model_dump()["sections"] is None
        assert "sections" not in edge.model_dump(exclude_none=True)
        assert edge.model_dump(include={"sources"}) == {"sources": [root.wire_id()]}
