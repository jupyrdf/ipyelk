# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Optional

import networkx as nx

from ...diagram import Diagram
from ...elements import HierarchicalIndex, Label, Node, Registry, index
from ...pipes import MarkElementWidget
from ..loader import Loader
from .nxutils import (
    from_nx_node,
    get_owner,
    get_root,
    process_endpoints,
    process_hierarchy,
)


class NXLoader(Loader):
    def load(
        self,
        graph: nx.MultiDiGraph,
        hierarchy: Optional[nx.DiGraph] = None,
    ) -> MarkElementWidget:
        hierarchy = process_hierarchy(graph, hierarchy)

        # add graph nodes
        nodes = []
        for n in graph.nodes():
            el = from_nx_node(n, graph)
            nodes.append(el)
            if not el.labels:
                el.labels.append(Label(text=el.get_id()))

        # add hierarchy nodes
        for n in hierarchy.nodes():
            if n not in graph:
                el = from_nx_node(n, hierarchy)
                nodes.append(el)

        context = Registry()
        with context:
            el_map = HierarchicalIndex.from_els(*nodes)

            # nest elements based on hierarchical edges
            for u, v in hierarchy.edges():
                parent = u if isinstance(u, Node) else el_map.get(u)
                child = v if isinstance(v, Node) else el_map.get(v)
                parent.add_child(child)

            # add element edges
            for u, v, d in graph.edges(data=True):
                edge = process_endpoints(u, v, d, el_map)
                owner = get_owner(edge, hierarchy, el_map)
                owner.edges.append(edge)

            root: Node = get_root(hierarchy)
            if not isinstance(root, Node):
                root = el_map.get(root)

            for el in index.iter_elements(root):
                el.id = el.get_id()

        return MarkElementWidget(
            value=self.apply_layout_defaults(root),
        )


def from_nx(graph, hierarchy=None, **kwargs):
    diagram = Diagram(
        source=NXLoader().load(graph=graph, hierarchy=hierarchy), **kwargs
    )
    return diagram
