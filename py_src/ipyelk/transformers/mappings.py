# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass
from typing import Dict, Hashable, Iterator, List, Optional

from .. import elements  # import Mark, Node, BaseElement
from ..model.model import ElkNode, ElkPort


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Optional[Hashable]
    target: Hashable
    target_port: Optional[Hashable]
    owner: Hashable
    data: Dict
    mark: Optional[elements.Mark]

    def __hash__(self):
        return hash((self.source, self.source_port, self.target, self.target_port))


@dataclass(frozen=True)
class Port:
    node: Hashable
    elkport: ElkPort
    mark: Optional[elements.Mark]

    def __hash__(self):
        return hash(tuple([hash(self.node), hash(self.elkport.id)]))


# TODO investigating following pattern for various map
# https://github.com/pandas-dev/pandas/issues/33025#issuecomment-699636759
NodeMap = Dict[Hashable, ElkNode]
EdgeMap = Dict[Hashable, List[Edge]]
PortMap = Dict[Hashable, Port]

#########################################################
# TODO better place for these functions to live?
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


def iter_elements(el: elements.BaseElement) -> Iterator[elements.BaseElement]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param el: current element
    :yield: sub element
    """
    if isinstance(el, elements.Node):
        for child in el.children:
            yield from iter_elements(child)
        for port in el.ports:
            yield from iter_elements(port)
        for edge in el.edges:
            yield from iter_elements(edge)
    for label in el.labels:
        yield from iter_elements(label)
    yield el


def extract_id(root: elements.BaseElement):
    return {
        el.id: el for el in iter_elements(root) if not isinstance(el, elements.Edge)
    }


def build_edge(edge, el_map):
    source = edge.get("source", edge["sources"][0])
    target = edge.get("target", edge["targets"][0])
    edge_dict = {**edge, "source": el_map[source], "target": el_map[target]}
    return elements.Edge(**edge_dict)


def link_edges(edges_map, el_map):
    for node_id, edges in edges_map.items():
        node = el_map.get(node_id)
        node.edges = [build_edge(e, el_map) for e in edges]


def node_from_elkjson(data):
    # extract_edges currently mutates `data` by popping the edge dict
    edges_map = extract_edges(data)  # dict of node.id to edge list
    root = elements.Node(**data)  # element hierarchy without edges
    el_map = extract_id(root)  # get dict of id to element
    # reapplies edges to `data`
    link_edges(edges_map, el_map)
    apply_edges(data, edges_map)
    return root


#########################################################
