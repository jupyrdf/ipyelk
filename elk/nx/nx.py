import json
import ipywidgets as W
import networkx as nx
import traitlets as T

from collections import defaultdict
from dataclasses import dataclass
from itertools import tee
from typing import (
    List,
    Dict,
    Hashable,
    Optional,
    Tuple,
    Set,
    Iterable,
    Generator,
    Iterator,
    Callable,
)

from ..app import ElkTransformer
from ..diagram.elk_model import ElkPort, ElkNode, ElkExtendedEdge, ElkLabel


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Hashable  # Optional?
    target: Hashable
    target_port: Hashable  # Optional?

    # @property
    # def edge_id(self):
    #     return "{}.{} -> {}.{}".format(
    #         self.source, self.source_port, self.target, self.target_port
    #     )

    # def port_id(self, port):
    #     pass

    # @property
    # def sources(self):
    #     return self.port_id(self.source, self.source_port)

    # @property
    # def targets(self):
    #     return self.port_id(self.target, self.target_port)


EdgeMap = Dict[Hashable, List[Edge]]


def get_roots(tree: nx.DiGraph, g: nx.DiGraph) -> Iterator[Hashable]:
    """Iterate through the roots in the tree and any orphaned nodes in the graph
    
    :param tree: Hierarchical graph
    :type tree: nx.DiGraph
    :param g: [description]
    :type g: nx.DiGraph
    :return: [description]
    :rtype: Hashable
    :yield: [description]
    :rtype: Hashable
    """
    assert nx.is_forest(
        tree
    ), "The given hierarchy should be a NetworkX DiGraph that is also a Forest"
    for node, degree in tree.in_degree():
        if degree == 0:
            yield node
    for node in g.nodes():
        if node not in tree:
            yield node


def compact(array: Optional[List]) -> Optional[List]:
    """Compact an list by removing `None` elements. If the result is an empty list, return `None`
    
    :param array: Inital list to compact
    :type array: List
    :return: Final compacted list or None
    :rtype: Optional[List]
    """
    if isinstance(array, dict):
        array = list(array.values())
    if isinstance(array, List):
        array = [e for e in array if e is not None]
        if len(array) > 0:
            return array
    return None


def get_edge_data(g: nx.DiGraph, source, target):
    if isinstance(g, nx.MultiDiGraph):
        return g.get_edge_data(source, target).values()
    return [g.get_edge_data(source, target)]


def closest_visible(tree: nx.DiGraph, node: Hashable, attr: str):
    """Crawl through the given NetworkX `tree` looking for an ancestor of `node` that is not hidden
    
    :param tree: [description] Ancestor graph
    :type tree: nx.DiGraph
    :param node: [description] Node to identify a visible ancestor
    :type node: Hashable
    :param attr: [description]
    :type attr: str The attribute saved to the ancestor graph tracking visibility
    :raises ValueError: [description]
    :return: [description]
    :rtype: [type]
    """
    if node not in tree:
        return None
    if not is_hidden(tree, node, attr):
        return node
    predecesors = list(tree.predecessors(node))
    assert (
        len(predecesors) <= 1
    ), f"Expected only a single parent for `{node}` not {len(predecesors)}"
    for pred in tree.predecessors(node):
        return closest_visible(tree, pred, attr)
    raise ValueError(f"Unable to find visible ancestor for `{node}`")


@dataclass(frozen=True)
class TunnelEdge:
    """Object to hold references to edges that are hidden"""

    source: Hashable
    target: Hashable
    sourcePort: Optional[Hashable] = None
    targetPort: Optional[Hashable] = None

    def closest(
        self, tree: nx.DiGraph, attr: str = "hidden"
    ) -> Tuple[Hashable, Hashable]:
        """Map this edge to the closest visible source and target for the given ancestor tree        
        :param tree: Ancestor Tree
        :type tree: nx.DiGraph
        :param attr: Attribute used to track if a node is hidden in the ancestor tree
        :type tree: str
        """
        assert self.source in tree, f"Expect source:`{self.source}` to be in the tree"
        assert self.target in tree, f"Expect target:`{self.target}` to be in the tree"
        source = closest_visible(tree, self.source, attr)
        target = closest_visible(tree, self.target, attr)
        # TODO look at edgeset and determine if there is an equivalent one
        return source, target


class XELK(ElkTransformer):
    """NetworkX DiGraphs to ELK dictionary structure"""

    HIDDEN_ATTR = "hidden"
    SIDES = {"input": "EAST", "output": "WEST"}
    _visible_edges: Optional[EdgeMap] = None
    _hidden_edges: Optional[EdgeMap] = None

    source = T.Tuple(
        T.Union([T.Instance(nx.DiGraph), T.Instance(nx.MultiDiGraph)]),
        T.Instance(nx.DiGraph, allow_none=True),
    )
    base_layout = T.Dict(kw={"hierarchyHandling": "INCLUDE_CHILDREN"})
    port_scale = T.Int(default_value=10)
    text_scale = T.Int(default_value=10)

    def eid(self, node: Hashable) -> str:
        """Get the element id for a node in the main graph for use in elk
        
        :param node: Node in main  graph
        :type node: Hashable
        :return: Element ID
        :rtype: str
        """
        g, tree = self.source
        if node is None:
            return "root"
        elif node in g:
            return g.nodes[node].get("_id", f"{node}")
        return f"{node}"

    def port_id(self, node, port):
        return f"{self.eid(node)}.{port}"

    def edge_id(self, edge: Edge):
        # TODO probably will need more sophisticated id generation in future
        return "{}.{} -> {}.{}".format(
            edge.source, edge.source_port, edge.target, edge.target_port
        )

    def transform(self, root=None):
        """Generate ELK dictionary structure
        :param root: [description], defaults to None
        :type root: [type], optional
        :return: [description]
        :rtype: [type]
        """
        if root is None:
            # clear old cached info is starting at the top level transform
            self._nodes: Dict[Hashable, ElkNode] = {}
            self._ports: Dict[Tuple[Hashable, Hashable], ElkPort] = {}
            self._visible_edges, self._hidden_edges = self.collect_edges()
        elif self.is_hidden(root):
            # bail is the node is hidden
            return None
        nodes = self._nodes
        ports = self._ports

        base_layout = self.base_layout
        g, tree = self.source

        if base_layout is None:
            base_layout = {}

        layout = {
            # 'algorithm': 'layered',
            # 'elk.edgeRouting': 'POLYLINE',
            # 'elk.portConstraints': 'FIXED_SIDE',
            # 'layering.strategy': 'NETWORK_SIMPEX'
        }

        layout.update(base_layout)

        properties = None
        # custom_css_classes =
        # if
        #     properties['cssClasses'] = " ".join()

        # edges = edge_dict.get(root)

        labels = self.make_labels(root)
        model_id = self.eid(root)

        # new_ports = self.get_ports(root)
        # ports[model_id] = new_ports

        self._nodes[root] = ElkNode(
            id=model_id,
            labels=labels,
            layoutOptions=layout,
            children=compact(self.get_children(root)),
            # ports=compact(new_ports),
            # ports=compact(self.make_ports(root, self._visible_edges)),
            # width=width,
            # height=height,
            # edges=compact(self.make_edges(root, self._visible_edges)),
            properties=properties,
        )

        if root is None:
            # the top level of the transform

            port_style = ["slack-port"]
            edge_style = ["slack-edge"]
            nodes, ports = self.process_edges(nodes, ports, self._visible_edges)
            nodes, ports = self.process_edges(
                nodes, ports, self._hidden_edges, edge_style, port_style
            )

            for (owner, _), port in ports.items():
                node = nodes[owner]
                if node.ports is None:
                    node.ports = []
                node.ports += [port]
            # nodes = self.post_transform(nodes, ports, self._hidden_edges)

            nodes = self.size_nodes(nodes)

        return nodes[root]  # top level node

    def size_nodes(self, nodes: Dict[Hashable, ElkNode]) -> Dict[Hashable, ElkNode]:
        for node in nodes.values():
            node.width, node.height = self.get_node_size(node)
        return nodes

    def process_edges(
        self, nodes, ports, edges: EdgeMap, edge_style=None, port_style=None
    ):

        for owner, edges in edges.items():
            for edge in edges:
                node = nodes[owner]
                if node.edges is None:
                    node.edges = []

                node.edges += [self.make_edge(edge, edge_style)]
                source_var = (edge.source, edge.source_port)
                if source_var not in ports:
                    ports[source_var] = self.make_port(
                        edge.source, edge.source_port, port_style
                    )
                target_var = (edge.target, edge.target_port)
                if target_var not in ports:
                    ports[target_var] = self.make_port(
                        edge.target, edge.target_port, port_style
                    )
        return nodes, ports

    def make_edge(
        self, edge: Edge, styles: Optional[List[str]] = None
    ) -> ElkExtendedEdge:
        properties = None
        if styles:
            properties = dict(cssClasses=" ".join(styles))

        return ElkExtendedEdge(
            id=self.edge_id(edge),
            sources=[self.port_id(edge.source, edge.source_port)],
            targets=[self.port_id(edge.target, edge.target_port)],
            properties=properties,
        )

    def make_port(self, owner, port, styles):
        properties = None
        if styles:
            properties = dict(cssClasses=" ".join(styles))

        return ElkPort(
            id=self.port_id(owner, port),
            height=0.5 * self.port_scale,
            width=0.5 * self.port_scale,
            properties=properties,
        )

    def post_transform(
        self,
        nodes: Dict[str, ElkNode],
        ports: Dict[str, Dict[str, ElkPort]],
        hidden_edges: EdgeMap,
    ) -> Dict[str, ElkNode]:
        """Transform the given elk nodes by adding information from the hidden_edges. (extra ports / edges and a different level of abstraction then shown)
        
        :param elk_nodes: Given dictionary of elk nodes
        :type elk_nodes: Dict[str, ElkNode]
        :param hidden_edges: List of hidden edges
        :type hidden_edges: List[TunnelEdge]
        :return: Updated dictionary of elk nodes
        :rtype: Dict[str, ElkNode] 
        """
        # return nodes

        # ports: Dict = {}

        # for node_id, node in nodes.items():
        #     ports = self.make_ports(node, hidden_edges, ["slack-port"])
        #     self.
        edge_properties = {"cssClasses": "slack-edge"}
        for owner, edges in hidden_edges.items():
            for edge in edges:
                node = nodes[owner]
                sources = self.port_id(edge.source, edge.source_port)
                targets = self.port_id(edge.target, edge.target_port)
                node.edges.append(
                    ElkExtendedEdge(
                        id=self.edge_id(edge),
                        sources=[sources],
                        targets=[targets],
                        properties=edge_properties,
                    )
                )
                # if sources not in

        return nodes

        for sources, targets in hidden_edges:
            for source, (h_s, h_sp) in sources:
                elk_nodes[source]
                for target, h_target in targets:
                    pass
                    # owner =
                    # elk_nodes[target]

        grouped_edges: Dict[
            Tuple[str, str], List[TunnelEdge]
        ] = self.group_hidden_edges(hidden_edges)

        for (source_id, target_id), edges in grouped_edges.items():
            if source_id != target_id:
                source_ports = {p.id: p for p in elk_nodes[source_id].ports}
                target_ports = {p.id: p for p in elk_nodes[target_id].ports}

                for edge in edges:
                    source_port = self.port_id(edge.source, edge.sourcePort)
                    target_port = self.port_id(edge.target, edge.targetPort)
                    if source_port in source_ports:
                        print("source in view redefine targetport")
                        target_port = self.port_id(target_id, edge.targetPort)
                    elif target_port in target_ports:
                        print("target in view redefine sourceport")
                        source_port = self.port_id(source_id, edge.sourcePort)
                    else:
                        print("bundle edges")

        return elk_nodes

    def make_ports(
        self,
        nodes: Dict[str, ElkNode],
        edge_dict: EdgeMap,
        styles: Optional[List[str]] = None,
    ) -> List[ElkPort]:
        #     properties={
        # #                         "elk.port.side": self.SIDES[direction],
        # #                         "cssClasses": "a p1",
        # #                     },
        properties = None
        if styles:
            properties = dict(cssClasses=" ".join(styles))

        for owner, edges in edge_dict.items():
            for edge in edges:
                if edge.source == node:
                    port_id = self.port_id(edge.source, edge.source_port)
                elif edge.target == node:
                    port_id = self.port_id(edge.target, edge.target)
                else:
                    continue
                ports.append(
                    ElkPort(
                        id=port_id,
                        height=0.5 * self.port_scale,
                        width=0.5 * self.port_scale,
                        properties=properties,
                    )
                )

        return [
            ElkPort(
                id=self.port_id(edge.source, edge.source_port),
                height=0.5 * self.port_scale,
                width=0.5 * self.port_scale,
                properties=properties,
            )
            for edge in edges
        ]

    def make_edges(
        self, node, edge_dict: EdgeMap, styles: Optional[List[str]] = None
    ) -> List[ElkExtendedEdge]:
        properties = None
        if styles:
            properties = dict(cssClasses=" ".join(styles))

        edges: List[Edge] = edge_dict.get(node, [])
        return [
            ElkExtendedEdge(
                id=self.edge_id(edge),
                sources=[self.port_id(edge.source, edge.source_port)],
                targets=[self.port_id(edge.target, edge.target_port)],
                properties=properties,
            )
            for edge in edges
        ]

    def group_hidden_edges(
        self, hidden_edges: List[TunnelEdge]
    ) -> Dict[Tuple[str, str], List[TunnelEdge]]:
        """Group the hidden edges by common visible source and target
        
        :param hidden_edges: List of hidden edges
        :type hidden_edges: List[TunnelEdge]
        :return: Grouped Hidden edges by source and target
        :rtype: Dict[Tuple[str, str], List[TunnelEdge]]
        """
        g, tree = self.source
        grouped: Dict[Tuple[str, str], List[TunnelEdge]] = defaultdict(list)
        for edge in hidden_edges:
            source, target = edge.closest(tree, self.HIDDEN_ATTR)
            grouped[self.eid(source), self.eid(target)].append(edge)

        return grouped

    def get_children(self, node) -> Optional[List[ElkNode]]:
        g, tree = self.source
        if node is None:
            if tree is None:
                # Nonhierarchical graph. Iterate over only the main graph
                return [self.transform(root=node) for node in g.nodes()]
            else:
                # Hierarchical graph but no specified root... start transforming from each root in the forest
                return [self.transform(root=node) for node in get_roots(tree, g)]

        else:
            if self.is_hidden(node):
                # Node is not Visible
                return None
            if tree is not None:
                # Node is visible and in the hierarchy
                return [self.transform(root=child) for child in tree.neighbors(node)]
        return None

    def get_node_size(self, node: ElkNode) -> Tuple[Optional[float], Optional[float]]:

        # if node is None:
        #     return None, None

        # g, tree = self.source
        # ins = g.in_edges(node)
        # outs = g.out_edges(node)

        if node.ports:
            height = (
                2 * self.port_scale * len(node.ports)
            )  # max(len(ins), len(outs))  # max number of ports
        else:
            height = 2 * self.port_scale

        if node.labels:
            width = self.text_scale * max(
                len(label.text or " ") for label in node.labels
            )
        else:
            width = self.text_scale

        # # data = g.nodes[node]
        # # name = data.get("_id", f"{node}")

        # width = self.text_scale * len(name)

        return width, height

    def make_labels(self, node) -> Optional[List[ElkLabel]]:
        if node is None:
            return None
        g, tree = self.source
        data = g.nodes[node]
        name = data.get("_id", f"{node}")
        width = self.text_scale * len(name)

        return [ElkLabel(id=f"{name}_label", text=name, width=width)]

    def get_ports(self, node) -> Dict[str, ElkPort]:
        if node is None:
            return []
        g, tree = self.source
        port_scale = self.port_scale

        ins = g.in_edges(node)
        outs = g.out_edges(node)

        port_index: Dict[str, ElkPort] = {}
        for direction, edge_group in zip(["input", "output"], [ins, outs]):
            for u, v in edge_group:
                for edge_data in get_edge_data(g, u, v):
                    # get port for the edge
                    io_port_attr = (
                        "sourcePort" if direction == "output" else "targetPort"
                    )
                    p = edge_data.get("port", None)

                    io_port = edge_data.get(io_port_attr, None) or p
                    port_id = self.port_id(node, io_port)
                    port_index[port_id] = ElkPort(
                        id=port_id,
                        height=0.5 * port_scale,
                        width=0.5 * port_scale,
                        properties={
                            "elk.port.side": self.SIDES[direction],
                            "cssClasses": "a p1",
                        },
                    )

        return port_index

    def collect_edges(self) -> Tuple[EdgeMap, EdgeMap]:
        """[summary]
        
        :return: [description]
        :rtype: Tuple[Dict[Hashable, List[ElkExtendedEdge]], Dict[Hashable, List[ElkExtendedEdge]]]
        """
        visible: EdgeMap = defaultdict(
            list
        )  # will index edges by nx.lowest_commen_ancestor
        hidden: EdgeMap = defaultdict(
            list
        )  # will index edges by nx.lowest_commen_ancestor

        g, tree = self.source

        factors = self.extract_factors()

        def merge(
            update: Dict[Hashable, List], base: Dict[Hashable, List]
        ) -> Dict[Hashable, List]:
            for key, value in update.items():
                base[key].extend(value)
            return base

        try:
            while True:
                sources, targets = next(factors)
                # Issue specifying hyperedge so expanding the source and target combinations....
                # for edge_dict in self.process_endpts(sources, targets):
                #     for owner, edges in edge_dict.items():
                #         visible[owner].extend(edges)
                visible = merge(self.process_endpts(sources, targets), visible)

        except StopIteration as e:
            hidden_factors: List[Tuple[List, List]] = e.value
            for sources, targets in hidden_factors:
                # for edge_dict in self.process_endpts(sources, targets):
                #     for owner, edges in edge_dict.items():
                #         hidden[owner].extend(edges)
                hidden = merge(self.process_endpts(sources, targets), hidden)

        return visible, hidden

    def to_dict(self) -> Dict:
        """Transform the NetworkX graphs into Elk json"""
        return self.transform().to_dict()

    def is_hidden(self, node):
        g, tree = self.source
        return is_hidden(tree, node, self.HIDDEN_ATTR)

    def extract_factors(
        self
    ) -> Generator[Tuple[List, List], None, List[Tuple[List, List]]]:
        g, tree = self.source
        grouped: List[Tuple[List, List]] = []

        for source_vars, target_vars in get_factors(g):
            shidden = [self.is_hidden(var[0]) for var in source_vars]
            thidden = [self.is_hidden(var[0]) for var in target_vars]

            sources = source_vars
            targets = target_vars

            vis_source = closest_common_visible(
                tree, [s for s, sp in source_vars], self.HIDDEN_ATTR
            )
            vis_target = closest_common_visible(
                tree, [t for t, tp in target_vars], self.HIDDEN_ATTR
            )

            if any(shidden) or any(thidden):
                if vis_source == vis_target:
                    # bail if factor is completely internal
                    continue

                # trim hidden...
                sources = list(keep(source_vars, invert(shidden)))
                targets = list(keep(target_vars, invert(thidden)))

                if all(shidden) or all(thidden):
                    if len(sources) == 0:
                        # source can be bundled...
                        #                     source_vars.sort()
                        sources = [(vis_source, v) for v in source_vars]

                    if len(targets) == 0:
                        # targets can be bundled...
                        target_vars.sort()
                        targets = [(vis_target, v) for v in target_vars]

                    grouped.append(
                        (sources, targets)
                    )  # [tuple(source_vars), tuple(target_vars)] = (vis_source, vis_target)
                    continue

            yield sources, targets
        return grouped

    def process_endpts(self, sources, targets) -> Dict[Hashable, List[Edge]]:
        g, tree = self.source

        edge_dict: Dict[Hashable, List[Edge]] = defaultdict(list)

        for s, sp in sources:
            # source_id = self.eid(s)
            # source_port = self.port_id(s, sp)

            for t, tp in targets:
                owner = closest_common_visible(tree, [s, t], self.HIDDEN_ATTR)
                # target_id = self.eid(s)
                # target_port = self.port_id(t, tp)
                edge_dict[owner].append(
                    Edge(source=s, source_port=sp, target=t, target_port=tp)
                )

        return edge_dict


def is_hidden(tree: nx.DiGraph, node: Hashable, attr="hidden") -> bool:
    """Iterate  on the node ancestors and determine if it is hidden along the chain"""
    if tree is not None and node in tree:
        if tree.nodes[node].get(attr, False):
            return True
        for ancestor in nx.ancestors(tree, node):
            if tree.nodes[ancestor].get(attr, False):
                return True
    return False


def lowest_common_ancestor(tree, nodes):
    if tree is None:
        return None
    while len(nodes) > 1:
        nodes = [
            lca(tree, u, v)
            for u, v in pairwise(nodes)  # can be more efficient than pairwise
        ]
    return nodes[0]


def lca(tree: nx.DiGraph, a: Hashable, b: Hashable) -> Optional[Hashable]:
    """Wrapper around the NetworkX `lowest_common_ancestor` but allows either source or target node to not be in the tree

    :param tree: Node hierarchy
    :type tree: nx.DiaGraph
    :param a: [description]
    :type a: Hashable
    :param b: [description]
    :type b: H
    :return: Common ancestor if it exists
    :rtype: [type]
    """
    if a in tree and b in tree:
        return nx.lowest_common_ancestor(tree, a, b)
    return None


def pairwise(iterable):
    """Chunk an interable into pairs

    Example:
        `> (s0,s1), (s1,s2), (s2, s3), ...`

    :param iterable: [description]
    :type iterable: [type]
    :return: [description]
    :rtype: [type]
    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def keep(items: Iterable[object], mask: Iterable[bool]) -> Iterable[object]:
    """Filter the items iterable based on the given mask
    
    :param items: Original iterable of objects
    :type items: Iterable[object]
    :param mask: Mask iterable to use as a filter
    :type mask: Iterable[Bool]
    :return: [description]
    :rtype: Iterable[object]
    :yield: Iterable of objects that pass the mask
    :rtype: Iterable[object]
    """
    for item, test in zip(items, mask):
        if test:
            yield item


def get_ports(edge_data: Dict) -> Tuple[str, str]:
    """Get the source and target ports."""
    p = edge_data.get("port", None)
    source_port = edge_data.get("sourcePort", None) or p
    target_port = edge_data.get("targetPort", None) or p
    return source_port, target_port


def get_factors(G: nx.MultiDiGraph) -> Generator[Tuple[List, List], None, None]:
    fg = nx.DiGraph()
    variables = set()
    for source, target, edge_data in G.edges(data=True):

        source_port, target_port = get_ports(edge_data)

        source_var = (source, source_port)
        target_var = (target, target_port)

        variables.add(source_var)
        variables.add(target_var)

        fg.add_node(source)
        fg.add_node(source_var)
        fg.add_node(target)
        fg.add_node(target_var)

        fg.add_edge(source, source_var)
        fg.add_edge(target, target_var)
        fg.add_edge(source_var, target_var)

    return split(fg.subgraph(variables))


def split(variable_graph: nx.DiGraph) -> Generator[Tuple[List, List], None, None]:
    for factor in nx.weakly_connected_components(variable_graph):
        sources = []
        targets = []
        for var in factor:
            if variable_graph.in_degree(var) == 0:
                sources.append(var)
            else:
                targets.append(var)

        assert len(sources) >= 1, "Expected at least one source"
        assert len(targets) >= 1, "Expected at least one target"
        yield sources, targets


def invert(mask):
    return map(lambda m: not m, mask)


def closest_common_visible(tree: nx.DiGraph, nodes, attr: str = "hidden") -> Hashable:
    if tree is None:
        return None
    return lowest_common_ancestor(tree, [closest_visible(tree, n, attr) for n in nodes])

