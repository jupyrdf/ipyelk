# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field

import networkx as nx

from .elements import BaseElement, Edge, Node
from .registry import Registry


@dataclass
class Mark:
    """Wrap the given node in another tuple so it can be used multiple times as
    a networkx node.

    :param node: Incoming Element to wrap
    :return: Tuple that describes this current node and context to be used in a
    networkx graph.
    """

    element: BaseElement
    context: Registry

    def __hash__(self):
        return hash((id(self.element), id(self.context)))

    def to_json(self):
        with self.context:
            return self.element.to_json()


@dataclass
class Compound:
    registry: Registry = field(default_factory=Registry)

    def _add(
        self, node: Node, g: nx.Graph, tree: nx.DiGraph, follow_edges: bool
    ) -> Mark:
        context = self.registry
        with context:
            nx_node = Mark(element=node, context=context)
            if nx_node not in g:
                g.add_node(nx_node, mark=nx_node, elkjson=node.to_json())

            for child in get_children(node):
                nx_child = self._add(child, g, tree, follow_edges=follow_edges)
                tree.add_edge(nx_node, nx_child)

            for edge in node._edges:
                endpts = edge.points()
                nx_u, nx_v = map(lambda n: Mark(element=n, context=context), endpts)
                for nx_pt, pt in zip([nx_u, nx_v], endpts):
                    if nx_pt not in g:
                        if follow_edges:
                            self._add(pt, g, tree, follow_edges=follow_edges)
                        else:
                            g.add_node(nx_pt, mark=nx_pt, elkjson=pt.to_json())

                assert isinstance(edge, Edge), f"Expected Edge type not {type(edge)}"
                g.add_edge(nx_u, nx_v, mark=Mark(edge, context), elkjson=edge.to_json())
            return nx_node

    def __call__(self, *nodes, follow_edges=True):
        g = nx.MultiDiGraph()
        tree = nx.DiGraph()
        for node in nodes:
            self._add(node, g, tree, follow_edges=follow_edges)
        return (g, tree)


def get_nodes(nodes):
    if isinstance(nodes, Node):
        nodes = [nodes]
    for node in nodes:
        yield node
        yield from get_children(node)


def get_children(node: Node):
    return getattr(node, "children", [])
