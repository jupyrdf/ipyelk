import json
import ipywidgets as W
import networkx as nx
import traitlets as T

from collections import defaultdict
from dataclasses import dataclass
from itertools import tee
from typing import (
    List,
    Dict,
    Hashable,
    Optional,
    Tuple,
    Set,
    Iterable,
    Generator,
    Iterator,
    Callable,
)

from ..app import ElkTransformer
from ..diagram.elk_model import ElkPort, ElkNode, ElkExtendedEdge, ElkLabel


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Hashable  # Optional?
    target: Hashable
    target_port: Hashable  # Optional?

EdgeMap = Dict[Hashable, List[Edge]]


def get_roots(tree: nx.DiGraph, g: nx.DiGraph) -> Iterator[Hashable]:
    """Iterate through the roots in the tree and any orphaned nodes in the graph
    
    :param tree: Hierarchical graph
    :type tree: nx.DiGraph
    :param g: [description]
    :type g: nx.DiGraph
    :return: [description]
    :rtype: Hashable
    :yield: [description]
    :rtype: Hashable
    """
    assert nx.is_forest(
        tree
    ), "The given hierarchy should be a NetworkX DiGraph that is also a Forest"
    for node, degree in tree.in_degree():
        if degree == 0:
            yield node
    for node in g.nodes():
        if node not in tree:
            yield node


def compact(array: Optional[List]) -> Optional[List]:
    """Compact an list by removing `None` elements. If the result is an empty list, return `None`
    
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


def get_edge_data(g: nx.DiGraph, source, target):
    if isinstance(g, nx.MultiDiGraph):
        return g.get_edge_data(source, target).values()
    return [g.get_edge_data(source, target)]


@dataclass(frozen=True)
class TunnelEdge:
    """Object to hold references to edges that are hidden"""

    source: Hashable
    target: Hashable
    sourcePort: Optional[Hashable] = None
    targetPort: Optional[Hashable] = None

    def closest(
        self, tree: nx.DiGraph, attr: str = "hidden"
    ) -> Tuple[Hashable, Hashable]:
        """Map this edge to the closest visible source and target for the given ancestor tree        
        :param tree: Ancestor Tree
        :type tree: nx.DiGraph
        :param attr: Attribute used to track if a node is hidden in the ancestor tree
        :type tree: str
        """
        assert self.source in tree, f"Expect source:`{self.source}` to be in the tree"
        assert self.target in tree, f"Expect target:`{self.target}` to be in the tree"
        source = closest_visible(tree, self.source, attr)
        target = closest_visible(tree, self.target, attr)
        # TODO look at edgeset and determine if there is an equivalent one
        return source, target


def lowest_common_ancestor(tree, nodes):
    if tree is None:
        return None
    while len(nodes) > 1:
        nodes = [
            lca(tree, u, v)
            for u, v in pairwise(nodes)  # can be more efficient than pairwise
        ]
    return nodes[0]


def lca(tree: nx.DiGraph, a: Hashable, b: Hashable) -> Optional[Hashable]:
    """Wrapper around the NetworkX `lowest_common_ancestor` but allows either source or target node to not be in the tree

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
        return nx.lowest_common_ancestor(tree, a, b)
    return None


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





def get_ports(edge_data: Dict) -> Tuple[str, str]:
    """Get the source and target ports."""
    p = edge_data.get("port", None)
    source_port = edge_data.get("sourcePort", None) or p
    target_port = edge_data.get("targetPort", None) or p
    return source_port, target_port
