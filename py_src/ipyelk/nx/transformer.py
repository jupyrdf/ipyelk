# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import logging
from collections import defaultdict
from functools import lru_cache
from typing import Dict, Generator, Hashable, List, Optional, Tuple

import networkx as nx
import traitlets as T

from ..app import ElkTransformer
from ..diagram.elk_model import ElkExtendedEdge, ElkLabel, ElkNode, ElkPort
from .factors import get_factors, invert, keep
from .nx import Edge, EdgeMap, compact, get_roots, lowest_common_ancestor

logger = logging.getLogger(__name__)


BASE_LAYOUT_DEFAULTS = {
    "hierarchyHandling": "INCLUDE_CHILDREN",
    # "algorithm": "layered",
    # "elk.edgeRouting": "POLYLINE",
    # "elk.portConstraints": "FIXED_SIDE",
    # "layering.strategy": "NETWORK_SIMPEX",
}


class XELK(ElkTransformer):
    """NetworkX DiGraphs to ELK dictionary structure"""

    HIDDEN_ATTR = "hidden"

    _hidden_edges: Optional[EdgeMap] = None
    _visible_edges: Optional[EdgeMap] = None

    source = T.Tuple(T.Instance(nx.Graph), T.Instance(nx.DiGraph, allow_none=True))
    base_layout = T.Dict(kw=BASE_LAYOUT_DEFAULTS)
    port_scale = T.Int(default_value=10)
    text_scale = T.Float(default_value=10)
    label_key = T.Unicode(default_value="label")
    label_offset = T.Float(default_value=5)

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

    def clear_cached(self):
        # clear old cached info is starting at the top level transform

        # TODO: look into ways to remove the need to have a cache like this
        # NOTE: this is caused by a series of side effects
        logger.debug("Clearing cached elk info")
        self._nodes: Dict[Hashable, ElkNode] = {}
        self._ports: Dict[Tuple[Hashable, Hashable], ElkPort] = {}
        self._visible_edges, self._hidden_edges = self.collect_edges()
        self.closest_common_visible.cache_clear()
        self.closest_visible.cache_clear()

    def transform(self, root=None):
        """Generate ELK dictionary structure
        :param root: [description], defaults to None
        :type root: [type], optional
        :return: [description]
        :rtype: [type]
        """
        try:
            g, tree = self.source
            if root is None:
                self.clear_cached()
            elif is_hidden(tree, root, self.HIDDEN_ATTR):
                # bail is the node is hidden
                return None
            nodes = self._nodes
            ports = self._ports

            base_layout = self.base_layout

            if base_layout is None:
                base_layout = {}

            layout = {}

            # TODO: refactor this so you can specify node-specific layouts
            # NOTE: add traitlet for it, and get based on node passed
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

                nodes = self.size_nodes(nodes)
        except Exception as E:
            logger.error("Error transforming elk graph")
            raise E

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

    def get_children(self, node) -> Optional[List[ElkNode]]:
        g, tree = self.source
        attr = self.HIDDEN_ATTR
        if node is None:
            if tree is None:
                # Nonhierarchical graph. Iterate over only the main graph
                return [self.transform(root=node) for node in g.nodes()]
            else:
                # Hierarchical graph but no specified root...
                # start transforming from each root in the forest
                return [self.transform(root=node) for node in get_roots(tree, g)]

        else:
            if is_hidden(tree, node, attr):
                # Node is not Visible
                return None
            if tree is not None:
                # Node is visible and in the hierarchy
                if node in tree:
                    return [
                        self.transform(root=child) for child in tree.neighbors(node)
                    ]
        return None

    def get_node_size(self, node: ElkNode) -> Tuple[Optional[float], Optional[float]]:
        height = 0
        if node.ports:
            height = (
                1.25 * self.port_scale * len(node.ports)
            )  # max(len(ins), len(outs))  # max number of ports
        height = max(18, height)
        if node.labels:
            width = (
                self.text_scale * max(len(label.text or " ") for label in node.labels)
                + self.label_offset
            )
        else:
            width = self.text_scale
        return width, height

    def make_labels(self, node) -> Optional[List[ElkLabel]]:
        if node is None:
            return None
        g, tree = self.source
        data = g.nodes[node]
        name = data.get(self.label_key, data.get("_id", f"{node}"))
        width = self.text_scale * len(name)

        return [
            ElkLabel(
                id=f"{name}_label_{node}",
                text=name,
                width=width,
                x=self.label_offset,
                y=self.label_offset,
            )
        ]

    def collect_edges(self) -> Tuple[EdgeMap, EdgeMap]:
        """[summary]

        :return: [description]
        :rtype: Tuple[
            Dict[Hashable, List[ElkExtendedEdge]],
            Dict[Hashable, List[ElkExtendedEdge]]
        ]
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
        self,
    ) -> Generator[Tuple[List, List], None, List[Tuple[List, List]]]:
        g, tree = self.source
        attr = self.HIDDEN_ATTR
        hidden: List[Tuple[List, List]] = []

        for source_vars, target_vars in get_factors(g):
            shidden = [is_hidden(tree, var[0], attr) for var in source_vars]
            thidden = [is_hidden(tree, var[0], attr) for var in target_vars]

            sources = source_vars
            targets = target_vars
            try:
                vis_source = self.closest_common_visible((s for s, sp in source_vars))
                vis_target = self.closest_common_visible((t for t, tp in target_vars))
            except ValueError:
                continue  # bail if no possible target or source
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

                    # [tuple(source_vars), tuple(target_vars)] = (
                    #   vis_source,
                    #   vis_target
                    # )
                    hidden.append((sources, targets))
                    continue

            yield sources, targets
        return hidden

    def process_endpts(self, sources, targets) -> Dict[Hashable, List[Edge]]:
        g, tree = self.source

        edge_dict: Dict[Hashable, List[Edge]] = defaultdict(list)

        for s, sp in sources:

            for t, tp in targets:
                owner = self.closest_common_visible((s, t))
                edge_dict[owner].append(
                    Edge(source=s, source_port=sp, target=t, target_port=tp)
                )

        return edge_dict

    @lru_cache()
    def closest_visible(self, node: Hashable):
        """Crawl through the given NetworkX `tree` looking for an ancestor of
        `node` that is not hidden

        :param node: [description] Node to identify a visible ancestor
        :type node: Hashable
        :raises ValueError: [description]
        :return: [description]
        :rtype: [type]
        """
        attr = self.HIDDEN_ATTR
        g, tree = self.source
        if node not in tree:
            return None
        if not is_hidden(tree, node, attr):
            return node
        predecesors = list(tree.predecessors(node))
        assert (
            len(predecesors) <= 1
        ), f"Expected only a single parent for `{node}` not {len(predecesors)}"
        for pred in tree.predecessors(node):
            return self.closest_visible(pred)
        raise ValueError(f"Unable to find visible ancestor for `{node}`")

    @lru_cache()
    def closest_common_visible(self, nodes: Tuple[Hashable]) -> Hashable:
        g, tree = self.source
        if tree is None:
            return None
        result = lowest_common_ancestor(tree, [self.closest_visible(n) for n in nodes])
        return result


def is_hidden(tree: nx.DiGraph, node: Hashable, attr: str) -> bool:
    """Iterate  on the node ancestors and determine if it is hidden along the chain"""
    if tree is not None and node in tree:
        if tree.nodes[node].get(attr, False):
            return True
        for ancestor in nx.ancestors(tree, node):
            if tree.nodes[ancestor].get(attr, False):
                return True
    return False
