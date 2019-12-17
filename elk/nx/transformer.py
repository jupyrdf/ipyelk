import networkx as nx
import traitlets as T

from collections import defaultdict
from typing import (
    List,
    Dict,
    Hashable,
    Optional,
    Tuple,
    Iterable,
    Generator,
    Iterator,
    Callable,
)

from ..app import ElkTransformer
from ..diagram.elk_model import ElkPort, ElkNode, ElkExtendedEdge, ElkLabel

from .nx import EdgeMap, Edge, compact, get_edge_data, get_roots, lowest_common_ancestor
from .factors import invert, keep, get_factors


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
        g, tree = self.source
        if root is None:
            # clear old cached info is starting at the top level transform
            self._nodes: Dict[Hashable, ElkNode] = {}
            self._ports: Dict[Tuple[Hashable, Hashable], ElkPort] = {}
            self._visible_edges, self._hidden_edges = self.collect_edges()
        elif is_hidden(tree, root, self.HIDDEN_ATTR):
            # bail is the node is hidden
            return None
        nodes = self._nodes
        ports = self._ports

        base_layout = self.base_layout
        

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

        labels = self.make_labels(root)
        model_id = self.eid(root)

        self._nodes[root] = ElkNode(
            id=model_id,
            labels=labels,
            layoutOptions=layout,
            children=compact(self.get_children(root)),
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

        for owner, edge_list in edges.items():
            for edge in edge_list:
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
        nodes: Dict[Hashable, ElkNode],
        ports: Dict[Hashable, Dict[Hashable, ElkPort]],
        hidden_edges: EdgeMap,
    ) -> Dict[Hashable, ElkNode]:
        """Transform the given elk nodes by adding information from the hidden_edges. (extra ports / edges and a different level of abstraction then shown)
        
        :param elk_nodes: Given dictionary of elk nodes
        :type elk_nodes: Dict[str, ElkNode]
        :param hidden_edges: List of hidden edges
        :type hidden_edges: List[TunnelEdge]
        :return: Updated dictionary of elk nodes
        :rtype: Dict[str, ElkNode] 
        """
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

    def get_children(self, node) -> Optional[List[ElkNode]]:
        g, tree = self.source
        attr = self.HIDDEN_ATTR
        if node is None:
            if tree is None:
                # Nonhierarchical graph. Iterate over only the main graph
                return [self.transform(root=node) for node in g.nodes()]
            else:
                # Hierarchical graph but no specified root... start transforming from each root in the forest
                return [self.transform(root=node) for node in get_roots(tree, g)]

        else:
            if is_hidden(tree, node, attr):
                # Node is not Visible
                return None
            if tree is not None:
                # Node is visible and in the hierarchy
                if node in tree:
                    return [self.transform(root=child) for child in tree.neighbors(node)]
        return None

    def get_node_size(self, node: ElkNode) -> Tuple[Optional[float], Optional[float]]:
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
        return width, height

    def make_labels(self, node) -> Optional[List[ElkLabel]]:
        if node is None:
            return None
        g, tree = self.source
        data = g.nodes[node]
        name = data.get("label", data.get("_id", f"{node}"))
        width = self.text_scale * len(name)

        return [ElkLabel(id=f"{name}_label", text=name, width=width)]

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
                visible = merge(self.process_endpts(sources, targets), visible)

        except StopIteration as e:
            hidden_factors: List[Tuple[List, List]] = e.value
            for sources, targets in hidden_factors:
                hidden = merge(self.process_endpts(sources, targets), hidden)

        return visible, hidden

    def to_dict(self) -> Dict:
        """Transform the NetworkX graphs into Elk json"""
        return self.transform().to_dict()

    def extract_factors(
        self
    ) -> Generator[Tuple[List, List], None, List[Tuple[List, List]]]:
        g, tree = self.source
        attr = self.HIDDEN_ATTR
        hidden: List[Tuple[List, List]] = []

        for source_vars, target_vars in get_factors(g):
            shidden = [is_hidden(tree, var[0], attr) for var in source_vars]
            thidden = [is_hidden(tree, var[0], attr) for var in target_vars]

            sources = source_vars
            targets = target_vars

            vis_source = closest_common_visible(tree, [s for s, sp in source_vars], attr)
            vis_target = closest_common_visible(tree, [t for t, tp in target_vars], attr)

            if any(shidden) or any(thidden):
                if vis_source == vis_target:
                    # bail if factor is completely internal
                    continue

                # trim hidden...
                sources = list(keep(source_vars, invert(shidden)))
                targets = list(keep(target_vars, invert(thidden)))

                if all(shidden) or all(thidden):
                    if len(sources) == 0:
                        sources = [(vis_source, v) for v in source_vars]

                    if len(targets) == 0:
                        target_vars.sort()
                        targets = [(vis_target, v) for v in target_vars]

                    hidden.append(
                        (sources, targets)
                    )  # [tuple(source_vars), tuple(target_vars)] = (vis_source, vis_target)
                    continue

            yield sources, targets
        return hidden

    def process_endpts(self, sources, targets) -> Dict[Hashable, List[Edge]]:
        g, tree = self.source
        attr = self.HIDDEN_ATTR

        edge_dict: Dict[Hashable, List[Edge]] = defaultdict(list)

        for s, sp in sources:

            for t, tp in targets:
                owner = closest_common_visible(tree, [s, t], attr)
                edge_dict[owner].append(
                    Edge(source=s, source_port=sp, target=t, target_port=tp)
                )

        return edge_dict

def is_hidden(tree:nx.DiGraph, node: Hashable, attr: str) -> bool:
    """Iterate  on the node ancestors and determine if it is hidden along the chain"""
    if tree is not None and node in tree:
        if tree.nodes[node].get(attr, False):
            return True
        for ancestor in nx.ancestors(tree, node):
            if tree.nodes[ancestor].get(attr, False):
                return True
    return False

def closest_visible(tree, node: Hashable, attr:str):
    """Crawl through the given NetworkX `tree` looking for an ancestor of `node` that is not hidden
    
    :param node: [description] Node to identify a visible ancestor
    :type node: Hashable
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

def closest_common_visible(tree: nx.DiGraph, nodes: Iterable[Hashable], attr:str) -> Hashable:
    if tree is None:
        return None
    return lowest_common_ancestor(tree, [closest_visible(tree, n, attr) for n in nodes])
