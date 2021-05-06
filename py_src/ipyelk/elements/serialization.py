# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict, Optional

from ipywidgets import DOMWidget
from pydantic import BaseModel

from .elements import Node
from .index import HierarchicalIndex, VisIndex


def pop_edges(data: Dict, edges=None):
    if edges is None:
        edges = {}

    if "edges" in data:
        edges[data["id"]] = data.pop("edges")
    for child in data.get("children", []):
        pop_edges(child, edges)
    return edges


def apply_edges(data: Dict, edges):
    node_id = data["id"]
    if node_id in edges:
        data["edges"] = edges.get(node_id)
    for child in data.get("children", []):
        apply_edges(child, edges)
    return edges


def convert_elkjson(data: Dict, vis_index: VisIndex = None) -> Node:
    # pop_edges currently mutates `data` by popping the edge dict
    edges_map = pop_edges(data)  # dict of node.id to edge list
    root = Node(**data)  # new element hierarchy without edges
    el_map = HierarchicalIndex.from_els(
        root, vis_index=vis_index
    )  # get mapping of ids to elements
    el_map.link_edges(edges_map)
    # reapplies edges to `data`
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
    if not js:
        return None
    return convert_elkjson(js)


elk_serialization = {"to_json": to_json, "from_json": from_elk_json}
symbol_serialization = {"to_json": to_json}
