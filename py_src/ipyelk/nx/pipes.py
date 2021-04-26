from typing import Dict, Hashable, Iterator, Optional

import ipywidgets as W
import networkx as nx
import traitlets as T

from ipyelk.elements import Edge, HierarchicalElement, Label, Node, Port, Registry
from ipyelk.elements.serialization import build_edge, build_shape_map, iter_elements

from .. import diagram
from ..elements import layout_options as opt
from ..pipes import BrowserTextSizer, ElkJS, Pipe, Pipeline

root_opts = opt.OptionsWidget(
    options=[
        opt.HierarchyHandling(),
    ],
).value
label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="center")]
).value
node_opts = opt.OptionsWidget(
    options=[
        opt.NodeSizeConstraints(),
    ],
).value


class NXSource(W.Widget):
    graph: nx.MultiDiGraph = T.Instance(nx.MultiDiGraph)
    hierarchy: nx.DiGraph = T.Instance(nx.DiGraph, allow_none=True)


class NetworkxPipe(Pipe):
    source: NXSource = T.Instance(NXSource, allow_none=True)

    async def run(self):
        """Run method"""
        # the things to make the stuff
        # self.value = elements
        graph = self.source.graph
        hierarchy = process_hierarchy(graph, self.source.hierarchy)
        root: Node = get_root(hierarchy)
        if not root.layoutOptions:
            root.layoutOptions = root_opts

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
            el_map = build_shape_map(*nodes)

            # nest elements based on hierarchical edges
            for u, v in hierarchy.edges():
                parent = u if isinstance(u, Node) else el_map[u]
                child = v if isinstance(v, Node) else el_map[v]
                parent.children.append(child)
            for u, v, d in graph.edges(data=True):
                e_dict = {**d, "source": u, "target": v}
                edge = build_edge(e_dict, el_map)
                owner = get_owner(edge, hierarchy, el_map)
                owner.edges.append(edge)

                for el in iter_elements(root):
                    el.id = el.get_id()

        self.value.value = root


class NXElkPipe(Pipeline):
    source: NXSource = T.Instance(NXSource, allow_none=True)

    @T.default("pipes")
    def _default_Pipes(self):
        return [
            NetworkxPipe(),
            BrowserTextSizer(),
            ElkJS(),
        ]


class Diagram(diagram.Diagram):
    source: NXSource = T.Instance(NXSource, allow_none=True)

    @T.default("pipe")
    def _default_Pipe(self):
        return NXElkPipe()


def from_nx_node(n: Hashable, d: Dict) -> Node:
    if isinstance(n, Node):
        el = n
    else:
        el = Node(**d)
        if el.id is None:
            el.id = str(n)
    return el


def iter_nx_sources(g: nx.DiGraph) -> Iterator[Hashable]:
    for node, in_degree in g.in_degree():
        if in_degree == 0:
            yield node


def single_root(g) -> bool:
    if len(g) == 0:
        return False
    return nx.is_tree(g)


def process_hierarchy(graph, hierarchy: Optional[nx.DiGraph]) -> nx.DiGraph:

    if hierarchy is None:
        hierarchy = nx.DiGraph()
    else:
        # copy graph to avoid mutation
        hierarchy = hierarchy.copy(as_view=False)

    if not single_root(hierarchy):
        # add new root and connect old roots to new root
        root = Node()
        hierarchy.add_node(root)

        # connect old roots to new root
        for n in iter_nx_sources(hierarchy):
            if n != root:
                hierarchy.add_edge(root, n)

    # check graph and add direction parentage to root if needed
    for n in graph.nodes():
        if n not in hierarchy:
            hierarchy.add_edge(root, n)

    return hierarchy


def get_root(hierarchy):
    for root in iter_nx_sources(hierarchy):
        return root


def as_in_hierarchy(node: HierarchicalElement, hierarchy, el_map):
    # TODO need to handle if given a port or node
    if isinstance(node, Port):
        node = node._parent

    if node in hierarchy:
        return node

    if isinstance(node, HierarchicalElement):
        node = node.get_id()
    else:
        # should be an identifer to something in the element map
        node = el_map[node]
        if isinstance(node, Port):
            node = node.parent
    assert node in hierarchy, "node not in hierarchy"
    return node


def lca(
    hierarchy: nx.DiGraph,
    node1: HierarchicalElement,
    node2: HierarchicalElement,
    el_map: Dict[str, HierarchicalElement],
) -> HierarchicalElement:
    node1 = as_in_hierarchy(node1, hierarchy, el_map)
    node2 = as_in_hierarchy(node2, hierarchy, el_map)

    ancestor = nx.lowest_common_ancestor(hierarchy, node1, node2)
    if not isinstance(ancestor, HierarchicalElement):
        ancestor = el_map[ancestor]
    return ancestor


def get_owner(edge: Edge, hierarchy, el_map) -> HierarchicalElement:
    u = edge.source
    v = edge.target
    return lca(hierarchy, u, v, el_map)
