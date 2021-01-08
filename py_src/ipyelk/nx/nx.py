# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass
from itertools import tee
from typing import Dict, Hashable, List, Optional, Tuple

import networkx as nx

from ..diagram.elk_model import ElkNode, ElkPort, ElkRoot


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Optional[Hashable]
    target: Hashable
    target_port: Optional[Hashable]
    owner: Hashable
    data: Optional[Dict]

    def __hash__(self):
        return hash((self.source, self.source_port, self.target, self.target_port))


@dataclass(frozen=True)
class Port:
    node: Hashable
    elkport: ElkPort

    def __hash__(self):
        return hash(tuple([hash(self.node), hash(self.elkport.id)]))


NodeMap = Dict[Hashable, ElkNode]
EdgeMap = Dict[Hashable, List[Edge]]
PortMap = Dict[Hashable, Port]


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
