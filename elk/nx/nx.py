import json
import ipywidgets as W
import networkx as nx
import traitlets as T

from collections import defaultdict
from typing import List, Dict, Hashable, Optional, Tuple, Set

from ..diagram.elk_model import ElkPort, ElkNode, ElkExtendedEdge, ElkLabel
from ..app import ElkTransformer
from dataclasses import dataclass


def get_roots(tree: nx.DiGraph):
    for node, degree in tree.in_degree():
        if degree == 0:
            yield node


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
    assert node in tree, f"`{node}` is not in the tree"
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
        #TODO look at edgeset and determine if there is an equivalent one
        return source, target


class XELK(ElkTransformer):
    """NetworkX DiGraphs to ELK dictionary structure"""

    _edges: Optional[Dict[Hashable, List[ElkExtendedEdge]]] = None
    _nodes: Optional[Dict[str, ElkNode]] = None
    HIDDEN_ATTR = "hidden"
    SIDES = {"input": "EAST", "output": "WEST"}

    base_layout = T.Dict(kw={"hierarchyHandling": "INCLUDE_CHILDREN"})
    graph = T.Union([T.Instance(nx.DiGraph), T.Instance(nx.MultiDiGraph)])
    port_scale = T.Int(default_value=10)
    text_scale = T.Int(default_value=10)
    tree = T.Instance(nx.DiGraph, allow_none=True)

    @T.observe("graph", "tree")
    def _clear_edge_cache(self, change: T.Bunch = None):
        self._edges = None

    def eid(self, node: Hashable) -> str:
        """Get the element id for a node in the main graph for use in elk
        
        :param node: Node in main  graph
        :type node: Hashable
        :return: Element ID
        :rtype: str
        """
        if node is None:
            return "root"
        elif node in self.graph:
            return self.graph.nodes[node].get("_id", f"{node}")
        return f"{node}"

    def transform(self, root=None):
        """Generate ELK dictionary structure
        :param root: [description], defaults to None
        :type root: [type], optional
        :return: [description]
        :rtype: [type]
        """
        children: List[ElkNode]
        base_layout = self.base_layout
        g = self.graph
        tree = self.tree

        if base_layout is None:
            base_layout = {}

        if root is None:
            self._nodes = {}
            self.collect_edges(refresh=True)  # clear old cached edges
            if tree is None:
                children = [self.transform(root=node) for node in g.nodes()]
            else:
                children = [self.transform(root=node) for node in get_roots(tree)]

        else:
            if is_hidden(self.tree, root, self.HIDDEN_ATTR):
                return None
            if tree is not None:
                children = [
                    self.transform(root=child) for child in tree.neighbors(root)
                ]

        # process children first remove `None` then if empty list set to None
        children = [c for c in children if c is not None]
        if len(children) == 0:
            children = None

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

        edges = self.edges.get(root)
        width, height = self.get_node_size(root)
        labels = self.make_labels(root)
        model_id = self.eid(root)

        self._nodes[model_id] = ElkNode(
            id=model_id,
            labels=labels,
            layoutOptions=layout,
            children=children,
            ports=self.get_ports(root),
            width=width,
            height=height,
            edges=edges,
            properties=properties,
        )

        if model_id is None:
            # the top level of the transform
            self._nodes = self.post_transform(self._nodes, self._hidden_edges)
        return self._nodes[model_id]  # top level node

    def post_transform(
        self, elk_nodes: Dict[str, ElkNode], hidden_edges: List[TunnelEdge]
    ) -> Dict[str, ElkNode]:
        """Transform the given elk nodes by adding information from the hidden_edges. (extra ports / edges and a different level of abstraction then shown)
        
        :param elk_nodes: Given dictionary of elk nodes
        :type elk_nodes: Dict[str, ElkNode]
        :param hidden_edges: List of hidden edges
        :type hidden_edges: List[TunnelEdge]
        :return: Updated dictionary of elk nodes
        :rtype: Dict[str, ElkNode] 
        """
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
                        print('source in view redefine targetport')
                        target_port = self.port_id(target_id, edge.targetPort)
                    elif target_port in target_ports:
                        print('target in view redefine sourceport')
                        source_port = self.port_id(source_id, edge.sourcePort)
                    else:
                        print('bundle edges')
                        #bundle


        # hidden_edges: List[
        #     TunnelEdge
        # ] = self._hidden_edges  # currently side effect from `self.collect_edges()`  :(
        # if hidden_edges:
        #     for edge in hidden_edges:
        #         source, target= edge.closest(
        #             self.tree, self.HIDDEN_ATTR
        #         )
        #         if source == target:
        #             #do not need to add an edge... may need to add port...
        #             ports = elk_nodes[self.eid(edge.source)].ports

        #             edge.sourcePort
        #             continue

        #         enoke = self._nodes[source]

        return elk_nodes

    def group_hidden_edges(
        self, hidden_edges: List[TunnelEdge]
    ) -> Dict[Tuple[str, str], List[TunnelEdge]]:
        """Group the hidden edges by common visible source and target
        
        :param hidden_edges: List of hidden edges
        :type hidden_edges: List[TunnelEdge]
        :return: Grouped Hidden edges by source and target
        :rtype: Dict[Tuple[str, str], List[TunnelEdge]]
        """
        grouped: Dict[Tuple[str, str], List[TunnelEdge]] = defaultdict(list)
        for edge in hidden_edges:
            source, target = edge.closest(self.tree, self.HIDDEN_ATTR)
            grouped[self.eid(source), self.eid(target)].append(edge)

        return grouped

    def get_node_size(self, node) -> Tuple[Optional[float], Optional[float]]:
        if node is None:
            return None, None
        g = self.graph
        ins = g.in_edges(node)
        outs = g.out_edges(node)
        height = 2 * self.port_scale * max(len(ins), len(outs))  # max number of ports

        data = g.nodes[node]
        name = data.get("_id", f"{node}")

        width = self.text_scale * len(name)

        return width, height

    def make_labels(self, node) -> Optional[List[ElkLabel]]:
        if node is None:
            return None
        g = self.graph
        data = g.nodes[node]
        name = data.get("_id", f"{node}")
        width = self.text_scale * len(name)

        return [ElkLabel(id=f"{name}_label", text=name, width=width)]

    def get_ports(self, node) -> Optional[List[ElkPort]]:
        if node is None:
            return None
        g = self.graph
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

        ports: List[ElkPort] = list(port_index.values())
        if len(ports) == 0:
            return None
        return ports

    def collect_edges(self, refresh=True) -> Dict[Hashable, List[ElkExtendedEdge]]:
        edges: Dict[Hashable, Dict[str, ElkExtendedEdge]] = defaultdict(
            dict
        )  # will index edges by nx.lowest_commen_ancestor
        hidden_edges: Set[TunnelEdge] = set()
        g = self.graph
        tree = self.tree

        if isinstance(tree, nx.MultiDiGraph):
            new_tree = nx.DiGraph()
            new_tree.add_nodes_from(tree.nodes(data=True))
            new_tree.add_edges_from(tree.edges())
            tree = new_tree

        for node in g.nodes():
            outs = g.out_edges(node)
            for source, target in outs:
                for edge_data in get_edge_data(g, source, target):
                    p = edge_data.get("port", None)
                    sourcePort = edge_data.get("sourcePort", None) or p
                    targetPort = edge_data.get("targetPort", None) or p
                    if any(
                        is_hidden(tree, n, self.HIDDEN_ATTR) for n in [source, target]
                    ):
                        # TODO make this a new object `TunnelingEdge`?
                        hidden_edges.add(
                            TunnelEdge(
                                source=source,
                                target=target,
                                sourcePort=sourcePort,
                                targetPort=targetPort,
                            )
                        )
                        continue

                    # TODO handle non-port edges
                    assert sourcePort is not None and targetPort is not None
                    eid = edge_data.get(
                        "_id", f"{source}.{sourcePort} -> {target}.{targetPort}"
                    )

                    ancestor = lowest_common_ancestor(tree, source, target)
                    edges[ancestor][eid] = ElkExtendedEdge(
                        id=eid,
                        sources=[self.port_id(source, sourcePort)],
                        targets=[self.port_id(target, targetPort)],
                    )

        # Convert edge dictionary  into list
        filtered_edges = {k: list(e.values()) for k, e in edges.items()}
        if refresh:
            self._edges = filtered_edges
        self._hidden_edges = list(hidden_edges)
        return filtered_edges

    @property
    def edges(self) -> Dict[Hashable, List[ElkExtendedEdge]]:
        if self._edges is None:
            self._edges = self.collect_edges()
        return self._edges

    def port_id(self, node, port):
        return f"{self.eid(node)}.{port}"
        # return f"{self.eid(n)}.{e}_{self.SIDES.get(direction, direction)}"

    def to_dict(self) -> Dict:
        """Transform the NetworkX graphs into Elk json"""
        return self.transform().to_dict()


def is_hidden(tree: nx.DiGraph, node: Hashable, attr="hidden") -> bool:
    """Iterate  on the node ancestors and determine if it is hidden along the chain"""
    if tree is not None and node in tree:
        if tree.nodes[node].get(attr, False):
            return True
        for ancestor in nx.ancestors(tree, node):
            if tree.nodes[ancestor].get(attr, False):
                return True
    return False


def lowest_common_ancestor(tree, source, target):
    if tree is None:
        return None
    return nx.lowest_common_ancestor(tree, source, target)
