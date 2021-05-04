# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict, Hashable, Iterator, Optional

import ipywidgets as W
import networkx as nx
import traitlets as T

from .. import diagram
from ..elements import (
    EMPTY_SENTINEL,
    Edge,
    HierarchicalElement,
    HierarchicalIndex,
    Label,
    Node,
    Port,
    Registry,
    index,
)
from ..elements import layout_options as opt
from ..exceptions import NotFoundError
from ..pipes import (
    BrowserTextSizer,
    ElkJS,
    MarkElementWidget,
    Pipe,
    Pipeline,
    VisibilityPipe,
)
from ..tools import Loader

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
                parent.children.append(child)

            # add element edges
            for u, v, d in graph.edges(data=True):
                edge = process_endpoints(u, v, d, el_map)
                owner = get_owner(edge, hierarchy, el_map)
                owner.edges.append(edge)

            for el in index.iter_elements(root):
                el.id = el.get_id()

        return MarkElementWidget(value=root)


class NXSource(W.Widget):
    graph: nx.MultiDiGraph = T.Instance(nx.MultiDiGraph)
    hierarchy: nx.DiGraph = T.Instance(nx.DiGraph, allow_none=True)


class NetworkxPipe(Pipe):
    inlet: NXSource = T.Instance(NXSource, allow_none=True)

    async def run(self):
        """Run method"""
        # the things to make the stuff
        # self.value = elements
        graph = self.inlet.graph
        hierarchy = process_hierarchy(graph, self.inlet.hierarchy)
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
                parent.children.append(child)

            # add element edges
            for u, v, d in graph.edges(data=True):
                edge = process_endpoints(u, v, d, el_map)
                owner = get_owner(edge, hierarchy, el_map)
                owner.edges.append(edge)

            for el in index.iter_elements(root):
                el.id = el.get_id()

        self.outlet.value = root


class NXElkPipe(Pipeline):
    inlet: NXSource = T.Instance(NXSource, allow_none=True)

    @T.default("pipes")
    def _default_pipes(self):
        return [
            NetworkxPipe(),
            BrowserTextSizer(),
            # Toolcollapser(),
            VisibilityPipe(
                # tool = ToolCollapser(),
            ),
            ElkJS(),
            # SprottyViewer(),
            # Downselect(),
            # MiniSprottyViewer(),
        ]


class Diagram(diagram.Diagram):
    source: NXSource = T.Instance(NXSource, allow_none=True)

    @T.default("pipe")
    def _default_Pipe(self):
        return NXElkPipe()


def process_endpoints(
    u: Hashable, v: Hashable, data: Dict, el_map: HierarchicalIndex
) -> Edge:
    """Process the edge (u,v,data) for `sourcePort` `targetPort` and return Edge

    :param u: nx edge source
    :param v: nx edge target
    :param data: nx edge data
    :param el_map: Element map
    :return: new edge
    """
    # check data if it contains "sourcePort" or "targetPort" and point to the
    # appropriate `source` and `target`
    ends = {
        "source": get_endpoint(el_map, u),
        "target": get_endpoint(el_map, v),
    }
    for key, pt in ends.items():
        for attr in [key + "Port", "port"]:
            if attr in data:
                port = get_endpoint(el_map, pt, data[attr])
                assert isinstance(port, Port)
                ends[key] = port
                break  # don't try other attr combinations
    edge_dict = {**data, **ends}
    return Edge(**edge_dict)


def get_endpoint(
    el_map: HierarchicalIndex, pt: Hashable, port_key=EMPTY_SENTINEL
) -> HierarchicalElement:
    if not isinstance(pt, HierarchicalElement):
        pt = el_map.get(str(pt))  # must at least be an identifier in the element map
    if port_key is EMPTY_SENTINEL:
        return pt  # no need to try and resolve a port

    # easy check
    if isinstance(port_key, Port):
        assert port_key._parent is pt, "Expected port parent to be given endpoint"
        return port_key
    assert isinstance(pt, Node), f"Expect endpoint to be a `Node` not `{type(pt)}`"

    # attempt to find port using `port_key`
    try:
        port = pt.get_port(key=port_key)
    except NotFoundError as e:
        if port_key in el_map:
            el = el_map.get(port_key)  # port_key was a global id
            if isinstance(el, Port) and el._parent is pt:
                return el
            else:
                # TODO a new exception type?
                raise ValueError(
                    (
                        "Given `port_key:{port_key}`} maps to an global element "
                        "that isn't consistent with the edge."
                    )
                ) from e

        # okay to make a new port?
        port = pt.add_port(Port(width=5, height=5), key=port_key)
    return port


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


def as_in_hierarchy(node: HierarchicalElement, hierarchy, el_map: HierarchicalIndex):
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
    el_map: HierarchicalIndex,
) -> HierarchicalElement:
    node1 = as_in_hierarchy(node1, hierarchy, el_map)
    node2 = as_in_hierarchy(node2, hierarchy, el_map)

    ancestor = nx.lowest_common_ancestor(hierarchy, node1, node2)
    if not isinstance(ancestor, HierarchicalElement):
        ancestor = el_map[ancestor]
    return ancestor


def get_owner(
    edge: Edge, hierarchy: nx.DiGraph, el_map: HierarchicalIndex
) -> HierarchicalElement:
    u = edge.source
    v = edge.target
    return lca(hierarchy, u, v, el_map)
