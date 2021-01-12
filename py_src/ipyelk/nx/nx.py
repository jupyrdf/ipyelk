# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from itertools import tee
from typing import Dict, Hashable, List, Optional, Tuple

import networkx as nx

from ..diagram.elk_model import ElkNode, ElkRoot
from ..transform import NodeMap


def compact(array: Optional[List]) -> Optional[List]:
    """Compact an list by removing `None` elements. If the result is an empty
        list, return `None`

    :param array: Inital list to compact
    :type array: List
    :return: Final compacted list or None
    :rtype: Optional[List]
    """
    if isinstance(array, dict):
        array = list(array.values())
    if isinstance(array, List):
        array = [e for e in array if e is not None]
        if len(array) > 0:
            return array
    return None


def lowest_common_ancestor(tree, nodes):
    if tree is None:
        return ElkRoot
    while len(nodes) > 1:
        nodes = [
            lca(tree, u, v)
            for u, v in pairwise(nodes)  # TODO be more efficient than pairwise
        ]
    return nodes[0]


def lca(tree: nx.DiGraph, a: Hashable, b: Hashable) -> Optional[Hashable]:
    """Wrapper around the NetworkX `lowest_common_ancestor` but allows either
        source or target node to not be in the tree

    :param tree: Node hierarchy
    :type tree: nx.DiaGraph
    :param a: [description]
    :type a: Hashable
    :param b: [description]
    :type b: H
    :return: Common ancestor if it exists
    :rtype: [type]
    """
    if a in tree and b in tree:
        common = nx.lowest_common_ancestor(tree, a, b)
        if common in tree:
            return common
    return ElkRoot


def pairwise(iterable):
    """Chunk an interable into pairs

    Example:
        `> (s0,s1), (s1,s2), (s2, s3), ...`

    :param iterable: [description]
    :type iterable: [type]
    :return: [description]
    :rtype: [type]
    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def get_ports(edge_data: Dict) -> Tuple[Optional[Hashable], Optional[Hashable]]:
    """Get the source and target ports."""
    p = edge_data.get("port", None)
    source_port = edge_data.get("sourcePort", None) or p
    target_port = edge_data.get("targetPort", None) or p
    return source_port, target_port


def is_hidden(tree: nx.DiGraph, node: Hashable, attr: str) -> bool:
    """Iterate  on the node ancestors and determine if it is hidden along the chain"""
    if tree and node in tree:
        if tree.nodes[node].get(attr, False):
            return True
        for ancestor in nx.ancestors(tree, node):
            if tree.nodes[ancestor].get(attr, False):
                return True
    return False


def build_hierarchy(
    g: nx.Graph, tree: nx.DiGraph, elknodes: NodeMap, HIDDEN_ATTR: str
) -> List[ElkNode]:
    """The Elk JSON is hierarchical. This method iterates through the build
    elknodes and links children to parents if the incoming source includes a
    hierarcichal networkx diagraph tree.

    :param g: [description]
    :type g: nx.Graph
    :param tree: [description]
    :type tree: nx.DiGraph
    :param elknodes: mapping of networkx nodes to their elknode representations
    :type elknodes: NodeMap
    :param HIDDEN_ATTR: [description]
    :type HIDDEN_ATTR: str
    :return: Top level ElkNodes to put as children under the ElkRoot
    :rtype: List[ElkNode]
    """
    if tree:
        # roots of the tree
        roots = [n for n, d in tree.in_degree() if d == 0]
        for n, elknode in elknodes.items():
            if n in tree:
                elknode.children = [
                    elknodes[c]
                    for c in tree.neighbors(n)
                    if not is_hidden(tree, c, HIDDEN_ATTR)
                ]
            else:
                # nodes that are not in the tree
                roots.append(n)
    else:
        # only flat graph provided
        roots = []
        for n, elknode in elknodes.items():
            if not is_hidden(tree, n, HIDDEN_ATTR):
                roots.append(n)
    return [elknodes[n] for n in roots]


def map_visible(g: nx.Graph, tree: nx.DiGraph, attr: str) -> Dict[Hashable, Hashable]:
    """Build mapping of nodes to their closest visible node.
    If the node is not hidden then it would map to itself.

    :param g: [description]
    :type g: nx.Graph
    :param tree: [description]
    :type tree: nx.DiGraph
    :param attr: [description]
    :type attr: str
    :return: [description]
    :rtype: Dict[Hashable, Hashable]
    """
    mapping = {}
    if tree:
        for n in nx.algorithms.topological_sort(tree):
            if n in mapping:
                break  # go to next node in the sorting
            if not is_hidden(tree, n, attr):
                mapping[n] = n
            else:
                predecesors = list(tree.predecessors(n))
                assert len(predecesors) <= 1
                for last_visible in predecesors:
                    mapping[n] = last_visible
                    for d in nx.algorithms.dag.descendants(tree, n):
                        mapping[d] = last_visible

    # creating mapping entries for those nodes not in the tree
    for n in g.nodes():
        if n not in mapping:
            mapping[n] = n
    return mapping
