# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Optional

import networkx as nx

from ...diagram import Diagram
from ...elements import HierarchicalIndex, Label, Node, Registry, index
from ...elements import layout_options as opt
from ...pipes import MarkElementWidget, flows
from ...tools import Loader
from .nxutils import (
    from_nx_node,
    get_owner,
    get_root,
    process_endpoints,
    process_hierarchy,
)

root_opts = opt.OptionsWidget(
    options=[
        opt.HierarchyHandling(),
    ],
).value
label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center")]
).value
node_opts = opt.OptionsWidget(
    options=[
        opt.NodeSizeConstraints(),
    ],
).value


class NXLoader(Loader):
    def load(
        self, graph: nx.MultiDiGraph, hierarchy: Optional[nx.DiGraph] = None
    ) -> MarkElementWidget:
        hierarchy = process_hierarchy(graph, hierarchy)
        root: Node = get_root(hierarchy)
        if not root.layoutOptions:
            root.layoutOptions = root_opts

        # add graph nodes
        nodes = []
        for n, d in graph.nodes(data=True):
            el = from_nx_node(n, d)
            if not el.layoutOptions:
                el.layoutOptions = node_opts
            nodes.append(el)
            if not el.labels:
                el.labels.append(Label(text=el.id, layoutOptions=label_opts))

        # add hierarchy nodes
        for n, d in hierarchy.nodes(data=True):
            if n not in graph:
                el = from_nx_node(n, d)
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

            for el in index.iter_elements(root):
                el.id = el.get_id()

        return MarkElementWidget(
            value=root,
            flow=(flows.Layout,),
        )


def from_nx(graph, hierarchy=None, **kwargs):
    diagram = Diagram(
        source=NXLoader().load(graph=graph, hierarchy=hierarchy), **kwargs
    )
    return diagram
