# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict, Hashable, Iterator, Optional

import networkx as nx

from ...elements import (
    EMPTY_SENTINEL,
    Edge,
    HierarchicalElement,
    HierarchicalIndex,
    Node,
    Port,
)
from ...exceptions import NotFoundError


def process_endpoints(
    u: Hashable, v: Hashable, data: Dict, el_map: HierarchicalIndex
) -> Edge:
    """Process the edge (u,v,data) for `sourcePort` `targetPort` and return Edge

    :param u: nx edge source
    :param v: nx edge target
    :param data: nx edge data
    :param el_map: Element map
    :return: new edge
    """
    # check data if it contains "sourcePort" or "targetPort" and point to the
    # appropriate `source` and `target`
    ends = {
        "source": get_endpoint(el_map, u),
        "target": get_endpoint(el_map, v),
    }
    for key, pt in ends.items():
        for attr in [key + "Port", "port"]:
            if attr in data:
                port = get_endpoint(el_map, pt, data[attr])
                assert isinstance(port, Port)
                ends[key] = port
                break  # don't try other attr combinations
    edge_dict = {**data, **ends}
    return Edge(**edge_dict)


def get_endpoint(
    el_map: HierarchicalIndex, pt: Hashable, port_key=EMPTY_SENTINEL
) -> HierarchicalElement:
    if not isinstance(pt, HierarchicalElement):
        pt = el_map.get(str(pt))  # must at least be an identifier in the element map
    if port_key is EMPTY_SENTINEL:
        return pt  # no need to try and resolve a port

    # easy check
    if isinstance(port_key, Port):
        assert port_key._parent is pt, "Expected port parent to be given endpoint"
        return port_key
    assert isinstance(pt, Node), f"Expect endpoint to be a `Node` not `{type(pt)}`"

    # attempt to find port using `port_key`
    try:
        port = pt.get_port(key=port_key)
    except NotFoundError as e:
        if port_key in el_map:
            el = el_map.get(port_key)  # port_key was a global id
            if isinstance(el, Port) and el._parent is pt:
                return el
            else:
                # TODO a new exception type?
                raise ValueError(
                    (
                        "Given `port_key:{port_key}`} maps to an global element "
                        "that isn't consistent with the edge."
                    )
                ) from e

        # okay to make a new port?
        port = pt.add_port(Port(width=5, height=5), key=port_key)
    return port


def from_nx_node(n: Hashable, g: nx.Graph) -> Node:
    if isinstance(n, Node):
        el = n
    else:
        d = g.nodes[n]
        el = Node(**d)
        if el.id is None:
            el.id = str(n)
    return el


def iter_nx_sources(g: nx.DiGraph) -> Iterator[Hashable]:
    for node, in_degree in g.in_degree():
        if in_degree == 0:
            yield node


def single_root(g) -> bool:
    if len(g) == 0:
        return False
    return nx.is_tree(g)


def process_hierarchy(graph, hierarchy: Optional[nx.DiGraph]) -> nx.DiGraph:

    if hierarchy is None:
        hierarchy = nx.DiGraph()
    else:
        # copy graph to avoid mutation
        hierarchy = hierarchy.copy(as_view=False)

    # check graph and add any missing nodes
    for n in graph.nodes():
        if n not in hierarchy:
            hierarchy.add_node(n)

    if not single_root(hierarchy):
        # add new root and connect old roots to new root
        root = Node()
        hierarchy.add_node(root)

        # connect old roots to new root
        for n in iter_nx_sources(hierarchy):
            if n != root:
                hierarchy.add_edge(root, n)

    return hierarchy


def get_root(hierarchy):
    for root in iter_nx_sources(hierarchy):
        return root


def as_in_hierarchy(
    node: HierarchicalElement,
    hierarchy: nx.DiGraph,
    el_map: HierarchicalIndex,
    nx_node_map: Optional[Dict[Node, Hashable]] = None,
):
    """Attempts to convert node to how it appears in the hierarchical graph

    :param node: networkx graph of edges
    :param hierarchy: networkx tree of nodes
    :param el_map: element map of string ids to nodes
    :param nx_node_map: optional additional mapping of elements to their
    networkx node object
    :raises NotUniqueError: If multiple matching nodes in the hierarchy are found
    :raises NotFoundError: If unable to find a matching node
    :return: Node as it exists in the hierarchical graph
    """

    parent = node._parent if isinstance(node, Port) else node

    if parent in hierarchy:
        return parent
    elif nx_node_map and parent in nx_node_map:
        return nx_node_map[parent]

    if isinstance(parent, HierarchicalElement):
        node_id = parent.get_id()
        if node_id in hierarchy:
            return node_id
    else:
        # should be an identifer to something in the element map
        el = el_map[parent]
        if isinstance(el, Port):
            parent = el.parent
    if parent in hierarchy:
        return parent
    raise NotFoundError(f"Unable to find {node} in the hierarchy")


def lca(
    hierarchy: nx.DiGraph,
    node1: HierarchicalElement,
    node2: HierarchicalElement,
    el_map: HierarchicalIndex,
    nx_node_map: Optional[Dict[Node, Hashable]] = None,
) -> HierarchicalElement:
    """Find the lowest common ancestor between two nodes in the hierarchy. This
    is used to assign the correct edge owner based on it's source and target
    endpoints

    :param hierarchy: networkx tree hierarchy of nodes
    :param node1: node one
    :param node2: node two
    :param el_map: element map of string ids to nodes
    :return: Lowest Common Ancestor
    """
    node1 = as_in_hierarchy(node1, hierarchy, el_map, nx_node_map)
    node2 = as_in_hierarchy(node2, hierarchy, el_map, nx_node_map)

    ancestor = nx.lowest_common_ancestor(hierarchy, node1, node2)
    if not isinstance(ancestor, HierarchicalElement):
        ancestor = el_map[ancestor]
    return ancestor


def get_owner(
    edge: Edge,
    hierarchy: nx.DiGraph,
    el_map: HierarchicalIndex,
    nx_node_map: Optional[Dict[Node, Hashable]] = None,
) -> Node:
    u = edge.source
    v = edge.target
    owner = lca(hierarchy, u, v, el_map, nx_node_map)
    if isinstance(owner, Port):
        owner = owner.get_parent()
    assert isinstance(owner, Node)
    return owner
