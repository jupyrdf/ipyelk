# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field

import networkx as nx

from .elements import Node
from .registry import Registry


@dataclass
class Mark:
    """Wrap the given node in another tuple so it can be used multiple times as
    a networkx node.

    :param node: Incoming Node Element to wrap
    :type node: Node
    :return: Tuple that describes this current node and context to be used in a
    networkx graph.
    :rtype: Tuple[str, Node]
    """

    node: Node
    context: Registry

    def __hash__(self):
        return hash((id(self.node), id(self.context)))


# def Mark(node, context):
#     return (node, context)


@dataclass
class Compound:
    registry: Registry = field(default_factory=Registry)

    def _add(self, node, g, tree, follow_edges: bool):
        context = self.registry
        with context:
            nx_node = Mark(node=node, context=context)
            if nx_node not in g:
                g.add_node(nx_node, **node.to_json())

            for child in get_children(node):
                nx_child = self._add(child, g, tree, follow_edges=follow_edges)
                tree.add_edge(nx_node, nx_child)

            for edge in getattr(node, "_edges", []):
                endpts = edge.points()
                nx_u, nx_v = map(lambda n: Mark(node=n, context=context), endpts)
                for nx_pt, pt in zip([nx_u, nx_v], endpts):
                    if nx_pt not in g:
                        if follow_edges:
                            self._add(pt, g, tree, follow_edges=follow_edges)
                        else:
                            g.add_node(nx_pt, **pt.to_json())

                g.add_edge(nx_u, nx_v, **edge.to_json())
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
