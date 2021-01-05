# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field
from typing import Tuple, Union

import networkx as nx

from ...diagram.symbol import Symbol
from .elements import Node, Port
from .registry import Registry

def nx_wrap(node: Node, context: Registry) -> Tuple[str, Node]:
    """Wrap the given node in another tuple so it can be used multiple times as
    a networkx node.

    :param node: Incomming Node Element to wrap
    :type node: Node
    :return: Tuple that describes this current node and context to be used in a
    networkx graph.
    :rtype: Tuple[str, Node]
    """
    return (context, node)

def get_children(node: Node):
    return getattr(node, "children", [])

@dataclass
class Compound():
    registry: Registry = field(default_factory=Registry)

    def _add(self, node, g, tree):
        context = self.registry
        with context:
            nx_node = nx_wrap(node, context)
            if nx_node not in g:
                g.add_node(nx_node, **node.to_json())

            for edge in getattr(node, "_edges", []):
                endpts = edge.points()
                nx_u, nx_v = map(lambda n: nx_wrap(n, context), endpts)
                for nx_pt, pt in zip([nx_u, nx_v],endpts):
                    if nx_pt not in g:
                        g.add_node(nx_pt, **pt.to_json())

                g.add_edge(nx_u, nx_v, **edge.to_json())

            for child in get_children(node):
                nx_child = self._add(child, g, tree)
                tree.add_edge(nx_node, nx_child)
            return nx_node

    def __call__(self, *nodes):
        g = nx.MultiDiGraph()
        tree = nx.DiGraph()
        for node in nodes:
            self._add(node, g, tree)
        return (g, tree)


def get_nodes(nodes):
    if isinstance(nodes, Node):
        nodes = [nodes]
    for node in nodes:
        yield node
        yield from get_children(node)


def get_children(node: Node):
    return getattr(node, "children", [])


def nx_wrap(node: Node, context: Registry) -> Tuple[str, Node]:
    """Wrap the given node in another tuple so it can be used multiple times as
    a networkx node.

    :param node: Incomming Node Element to wrap
    :type node: Node
    :return: Tuple that describes this current node and context to be used in a
    networkx graph.
    :rtype: Tuple[str, Node]
    """
    return (context, node)
