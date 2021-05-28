# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict, Hashable, Optional

import networkx as nx
import traitlets as T

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
    root_id: str = T.Unicode(allow_none=True)

    def load(
        self,
        graph: nx.MultiDiGraph,
        hierarchy: Optional[nx.DiGraph] = None,
    ) -> MarkElementWidget:
        hierarchy = process_hierarchy(graph, hierarchy)

        # add graph nodes
        nx_node_map: Dict[Node, Hashable] = {}
        for n in graph.nodes():
            el = from_nx_node(n, graph)
            nx_node_map[el] = n
            if not el.labels:
                el.labels.append(Label(text=el.get_id()))

        # add hierarchy nodes
        for n in hierarchy.nodes():
            if n not in graph:
                el = from_nx_node(n, hierarchy)
                nx_node_map[el] = n

        context = Registry()
        with context:
            el_map = HierarchicalIndex.from_els(*nx_node_map.keys())

            # nest elements based on hierarchical edges
            for u, v in hierarchy.edges():
                parent = u if isinstance(u, Node) else el_map.get(u)
                child = v if isinstance(v, Node) else el_map.get(v)
                parent.add_child(child)

            # add element edges
            for u, v, d in graph.edges(data=True):
                edge = process_endpoints(u, v, d, el_map)
                owner = get_owner(edge, hierarchy, el_map, nx_node_map)
                owner.edges.append(edge)

            root: Node = get_root(hierarchy)
            if not isinstance(root, Node):
                root = el_map.get(root)

            if root.id is None and self.root_id is not None:
                root.id = self.root_id

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
