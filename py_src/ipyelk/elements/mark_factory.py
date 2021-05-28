# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Any, Optional

import networkx as nx
from pydantic import BaseModel, Field

from .elements import BaseElement, Edge, Node
from .registry import Registry


class Mark(BaseModel):
    """Wrap the given node in another tuple so it can be used multiple times as
    a networkx node.

    :param node: Incoming Element to wrap
    :return: Tuple that describes this current node and context to be used in a
    networkx graph.
    """

    element: BaseElement = Field(...)
    context: Registry = Field(...)
    selector: Optional[Any] = Field(None, exclude=True)

    def __hash__(self):
        return hash((id(self.element), id(self.context)))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def dict(self, **kwargs):
        with self.context:
            return self.element.dict(**kwargs)

    def get_selector(self):
        if isinstance(self.element, Edge):
            if self.selector is None:
                raise ValueError("Edge Selector not set")
            else:
                return self.selector
        else:
            return self

    def set_edge_selector(self, u, v, key):
        self.selector = (u, v, key)

    def get_id(self):
        with self.context:
            return self.element.get_id()


class MarkFactory(BaseModel):
    registry: Registry = Field(default_factory=Registry)

    def _add(
        self, node: Node, g: nx.Graph, tree: nx.DiGraph, follow_edges: bool
    ) -> Mark:
        context = self.registry
        with context:
            nx_node = Mark(element=node, context=context)
            if nx_node not in g:
                g.add_node(
                    nx_node,
                    mark=nx_node,
                    elkjson=node.dict(exclude={"children", "edges", "parent"}),
                )

            for child in get_children(node):
                nx_child = self._add(child, g, tree, follow_edges=follow_edges)
                tree.add_edge(nx_node, nx_child)

            for edge in node.edges:
                endpts = edge.points()
                nx_u, nx_v = map(lambda n: Mark(element=n, context=context), endpts)
                for nx_pt, pt in zip([nx_u, nx_v], endpts):
                    if nx_pt not in g:
                        if follow_edges:
                            self._add(pt, g, tree, follow_edges=follow_edges)
                        else:
                            g.add_node(
                                nx_pt,
                                mark=nx_pt,
                                elkjson=pt.dict(
                                    exclude={"children", "edges", "parent"}
                                ),
                            )

                assert isinstance(edge, Edge), f"Expected Edge type not {type(edge)}"
                mark = Mark(element=edge, context=context)
                key = g.add_edge(
                    nx_u,
                    nx_v,
                    mark=mark,
                    elkjson=edge.dict(),
                )
                mark.set_edge_selector(nx_u, nx_v, key)
            return nx_node

    def __call__(self, *nodes, follow_edges=True):
        g = nx.MultiDiGraph()
        tree = nx.DiGraph()
        for node in nodes:
            self._add(node, g, tree, follow_edges=follow_edges)
        return (g, tree)


def get_children(node: Node) -> Node:
    return getattr(node, "children", [])
