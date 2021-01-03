# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Tuple, Union

import networkx as nx

from ...diagram.symbol import Symbol
from .elements import Label, Node, Port
from .registry import Registry


@dataclass
class Connection:
    source: Union[Node, Port]
    target: Union[Node, Port]

    def to_json(self):
        data = {
            "id": Registry.get_id(self),
            "properties": {},
            "layoutOptions": {},
            "labels": [],
        }
        if isinstance(self.source, Port):
            data["sourcePort"] = Registry.get_id(self.source)
        if isinstance(self.target, Port):
            data["targetPort"] = Registry.get_id(self.target)
        return data

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source._parent
        v = self.target if isinstance(self.target, Node) else self.target._parent
        return u, v

    def __hash__(self):
        return id(self)


@dataclass
class Compound(Symbol):
    # TODO not sure how to compose these yet and if they are a kind of symbol
    registry: Registry = field(default_factory=Registry)

    nodes: set = field(default_factory=set)  # could be a set?
    edges: set = field(default_factory=set)  # could be a set?
    hierachical_edges: set = field(default_factory=set)  # could be a set?

    def connect(self, source, target, cls=Connection):
        self.add_node(source)
        self.add_node(target)
        c = cls(source, target)
        self.edges.add(c)
        return c

    def add_node(self, node: Union[Node, Port]):
        if isinstance(node, Port):
            self.nodes.add(node._parent)
        else:
            self.nodes.add(node)

    def source(self, *, context: Registry = None) -> Tuple[nx.MultiDiGraph, nx.DiGraph]:
        id_map = dict()
        g = nx.MultiDiGraph()
        tree = nx.DiGraph()

        if not isinstance(context, Registry):
            context = self.registry
        with context:
            for node in self:
                data = node.to_json()
                nx_node = nx_wrap(node, context)
                g.add_node(nx_node, **data)

                for child in get_children(node):
                    tree.add_edge(nx_node, nx_wrap(child, context))

            for edge in self.edges:
                # wrap the edge endpoints to be able to uniquely address the
                # node elements
                nx_u, nx_v = map(lambda n: nx_wrap(n, context), edge.points())
                g.add_edge(nx_u, nx_v, **edge.to_json())
        return (g, tree)

    def __iter__(self):
        """Iterate over the nodes and their children"""
        return get_nodes(self.nodes)


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
