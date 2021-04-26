from typing import Dict, Iterator, Optional

from ipywidgets import DOMWidget
from pydantic import BaseModel

from .elements import BaseElement, Edge, HierarchicalElement, Node

tmp = []


def extract_edges(data, edges=None):
    if edges is None:
        edges = {}

    if "edges" in data:
        edges[data["id"]] = data.pop("edges")
    for child in data.get("children", []):
        extract_edges(child, edges)
    return edges


def apply_edges(data, edges):
    node_id = data["id"]
    if node_id in edges:
        data["edges"] = edges.get(node_id)
    for child in data.get("children", []):
        apply_edges(child, edges)
    return edges


def iter_elements(*els: BaseElement) -> Iterator[BaseElement]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param el: current element
    :yield: sub element
    """
    for el in els:
        if isinstance(el, Node):
            yield from iter_elements(*el.children)
            yield from iter_elements(*el.ports)
            yield from iter_elements(*el.edges)

        yield from iter_elements(*el.labels)
        yield el


def build_shape_map(*root: BaseElement) -> Dict[str, HierarchicalElement]:
    return {
        el.get_id(): el
        for el in iter_elements(*root)
        if isinstance(el, HierarchicalElement)
    }


def build_edge(edge: Dict, el_map: Dict[str, HierarchicalElement]):
    source = edge.get("source")
    if source is None:
        source = edge["sources"][0]
    target = edge.get("target")
    if target is None:
        target = edge["targets"][0]
    edge_dict = {**edge, "source": el_map[source], "target": el_map[target]}
    return Edge(**edge_dict)


def link_edges(edges_map, el_map):
    for node_id, edges in edges_map.items():
        node = el_map.get(node_id)
        node.edges = [build_edge(e, el_map) for e in edges]


def node_from_elkjson(data):
    # extract_edges currently mutates `data` by popping the edge dict
    edges_map = extract_edges(data)  # dict of node.id to edge list
    root = Node(**data)  # element hierarchy without edges
    el_map = build_shape_map(root)  # get dict of id to element
    # reapplies edges to `data`
    tmp.append({"el_map": el_map, "edges_map": edges_map})
    link_edges(edges_map, el_map)
    apply_edges(data, edges_map)

    return root


def to_json(model: Optional[BaseModel], widget: DOMWidget) -> Optional[Dict]:
    """Function to serialize a dictionary of symbols for use in a diagram

    :param defs: dictionary of Symbols
    :param diagram: elk diagram widget
    :return: json dictionary
    """
    if model is None:
        return None
    return model.dict(exclude_none=True)


def from_elk_json(js: Optional[Dict], manager) -> Optional[Node]:
    if js is None:
        return None
    return node_from_elkjson(js)


elk_serialization = {"to_json": to_json, "from_json": from_elk_json}
symbol_serialization = {"to_json": to_json}
