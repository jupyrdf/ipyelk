# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from collections import defaultdict
from functools import lru_cache
from typing import Dict, Hashable, List, Optional, Set, Tuple, Type

import networkx as nx
import traitlets as T

import ipyelk.diagram.layout_options as opt

from ..diagram.elk_model import (
    ElkEdge,
    ElkExtendedEdge,
    ElkGraphElement,
    ElkLabel,
    ElkNode,
    ElkPort,
    ElkRoot,
)
from ..diagram.elk_text_sizer import ElkTextSizer, TextSize
from ..transform import ElkTransformer
from .nx import (
    Edge,
    EdgeMap,
    NodeMap,
    Port,
    PortMap,
    compact,
    get_ports,
    lowest_common_ancestor,
)


class XELK(ElkTransformer):
    """NetworkX DiGraphs to ELK dictionary structure"""

    HIDDEN_ATTR = "hidden"
    ELK_ROOT_ID = "root"

    _hidden_edges: Optional[EdgeMap] = None
    _visible_edges: Optional[EdgeMap] = None

    # internal map between output Elk Elements and incoming items
    _elk_to_item: Dict[str, Hashable] = None
    _item_to_elk: Dict[Hashable, str] = None

    source = T.Tuple(T.Instance(nx.Graph), T.Instance(nx.DiGraph, allow_none=True))
    layouts = T.Dict()  # keys: networkx nodes {ElkElements: {layout options}}
    css_classes = T.Dict()

    port_scale = T.Int(default_value=5)
    label_key = T.Unicode(default_value="labels")
    port_key = T.Unicode(default_value="ports")

    text_sizer: ElkTextSizer = T.Instance(ElkTextSizer, kw={}, allow_none=True)

    @T.default("source")
    def _default_source(self):
        return (nx.Graph(), None)

    @T.default("layouts")
    def _default_layouts(self):
        parent_opts = opt.OptionsWidget(
            identifier="parents",
            options=[
                opt.HierarchyHandling(),
            ],
        )
        label_opts = opt.OptionsWidget(
            identifier=ElkLabel, options=[opt.NodeLabelPlacement(horizontal="center")]
        )
        node_opts = opt.OptionsWidget(
            identifier=ElkNode,
            options=[
                opt.NodeSizeConstraints(),
            ],
        )

        default = opt.OptionsWidget(options=[parent_opts, node_opts, label_opts])
        return {ElkRoot: default.value}

    def node_id(self, node: Hashable) -> str:
        """Get the element id for a node in the main graph for use in elk

        :param node: Node in main  graph
        :type node: Hashable
        :return: Element ID
        :rtype: str
        """
        g, tree = self.source
        if node is ElkRoot:
            return "root"
        elif node in g:
            return g.nodes.get(node, {}).get("_id", f"{node}")
        return f"{node}"

    def port_id(self, node: Hashable, port: Optional[Hashable] = None) -> str:
        """Get a suitable Elk identifier from the node and port

        :param node: Node from the incoming networkx graph
        :type node: Hashable
        :param port: Port identifier, defaults to None
        :type port: Optional[Hashable], optional
        :return: If no port is provided will refer to the node
        :rtype: str
        """
        if port is None:
            return self.node_id(node)
        else:
            return f"{self.node_id(node)}.{port}"

    def edge_id(self, edge: Edge):
        # TODO probably will need more sophisticated id generation in future
        return "{}.{} -> {}.{}".format(
            edge.source, edge.source_port, edge.target, edge.target_port
        )

    def clear_cached(self):
        # clear old cached info is starting at the top level transform

        # TODO: look into ways to remove the need to have a cache like this
        # NOTE: this is caused by a series of side effects
        self.log.debug("Clearing cached elk info")
        self._elk_to_item: Dict[str, Hashable] = {}
        self._item_to_elk: Dict[Hashable, str] = {}
        self._ports: PortMap = {}
        self.closest_common_visible.cache_clear()
        self.closest_visible.cache_clear()

    async def transform(self) -> ElkNode:
        """Generate ELK dictionary structure
        :return: Root Elk node
        :rtype: ElkNode
        """
        # TODO decide behavior for nodes that exist in the tree but not g
        g, tree = self.source
        self.clear_cached()
        ports: PortMap = self._ports
        self._visible_edges, self._hidden_edges = self.collect_edges()

        # Process visible networkx nodes into elknodes
        visible_nodes = [
            n for n in g.nodes() if not is_hidden(tree, n, self.HIDDEN_ATTR)
        ]

        elknodes = {node: await self.make_elknode(node) for node in visible_nodes}
        top = self.build_hierarchy(elknodes)  # top level node

        # TODO flag to control if slack ports and edges should be hoisted to
        # closest visible ancestors
        port_style = {"slack-port"}
        edge_style = {"slack-edge"}

        elknodes, ports = await self.process_edges(elknodes, ports, self._visible_edges)
        elknodes, ports = await self.process_edges(
            elknodes, ports, self._hidden_edges, edge_style, port_style
        )

        # iterate through the port map and add ports to ElkNodes
        for port_id, port in ports.items():
            owner = port.node
            elkport = port.elkport
            elknode = elknodes[owner]
            if elknode.ports is None:
                elknode.ports = []
            # size port labels
            layout = self.get_layout(owner, ElkPort)
            elkport.layoutOptions = merge(elkport.layoutOptions, layout)
            elknode.ports += [elkport]

            self.register(elkport, port)
            # for label in listed(elkport.labels):
            #     self.register(label, port)

        # bulk calculate label sizes
        await self.size_labels(self.collect_labels(elknodes))
        # link children to parents
        self._nodes = elknodes

        for node, elk_node in elknodes.items():
            self.register(elk_node, node)
        return top

    def build_hierarchy(self, elknodes: NodeMap) -> ElkNode:
        """The Elk JSON is hierarchical. This method iterates through the build
        elknodes and links children to parents if the incoming source includes a
        hierarcichal networkx diagraph tree.

        :param elknodes: mapping of networkx nodes to their elknode representations
        :type elknodes: NodeMap
        :return: The root elknode
        :rtype: ElkNode
        """
        g, tree = self.source
        attr = self.HIDDEN_ATTR
        if tree:
            # roots of the tree
            roots = [n for n, d in tree.in_degree() if d == 0]
            for n, elknode in elknodes.items():
                if n in tree:
                    elknode.children = [
                        elknodes[c]
                        for c in tree.neighbors(n)
                        if not is_hidden(tree, c, attr)
                    ]
                else:
                    # nodes that are not in the tree
                    roots.append(n)
        else:
            # only flat graph provided
            roots = []
            for n, elknode in elknodes.items():
                if not is_hidden(tree, n, attr):
                    roots.append(n)

        top = ElkNode(
            id=self.ELK_ROOT_ID,
            children=[elknodes[n] for n in roots],
            layoutOptions=self.get_layout(ElkRoot, "parents"),
        )
        elknodes[ElkRoot] = top  # using `None` to represent root elknode
        return top  # returns top level node

    async def make_elknode(self, node) -> ElkNode:
        layout = self.get_layout(node, ElkNode)

        labels = await self.make_labels(node)
        properties = None
        css = self.get_css(node, ElkNode)
        if css:
            properties = dict(cssClasses=" ".join(css))

        # update port map with declared ports in the networkx node data
        node_ports = await self.collect_ports(node)
        for key, value in node_ports.items():
            self._ports[key] = value

        elk_node = ElkNode(
            id=self.node_id(node),
            labels=labels,
            layoutOptions=layout,
            properties=properties,
        )
        return elk_node

    def get_layout(
        self, node: Hashable, elk_type: Type[ElkGraphElement]
    ) -> Optional[Dict]:
        """Get the Elk Layout Options appropriate for given networkx node and
        filter by given elk_type

        :param node: [description]
        :type node: Hashable
        :param elk_type: [description]
        :type elk_type: Type[ElkGraphElement]
        :return: [description]
        :rtype: [type]
        """
        # TODO look at self.source hierarchy and resolve layout with added
        # infomation. until then use root node `None` for layout options
        if node not in self.layouts:
            node = ElkRoot

        type_opts = self.layouts.get(node, {})
        options = {**type_opts.get(elk_type, {})}
        if options:
            return options

    def get_css(
        self,
        node: Hashable,
        elk_type: Type[ElkGraphElement],
        dom_classes: Set[str] = None,
    ) -> Set[str]:
        """Get the CSS Classes appropriate for given networkx node given
        elk_type

        :param node: Networkx node
        :type node: Hashable
        :param elk_type: ElkGraphElement to get appropriate css classes
        :type elk_type: Type[ElkGraphElement]
        :param dom_classes: Set of base CSS DOM classes to merge, defaults to
        Set[str]=None
        :type dom_classes: [type], optional
        :return: Set of CSS Classes to apply
        :rtype: Set[str]
        """
        typed_css = self.css_classes.get(node, {})
        css_classes = set(typed_css.get(elk_type, []))
        if dom_classes is None:
            return css_classes
        return css_classes | dom_classes

    async def process_edges(
        self,
        nodes: NodeMap,
        ports: PortMap,
        edges: EdgeMap,
        edge_style: Set[str] = None,
        port_style: Set[str] = None,
    ) -> Tuple[NodeMap, PortMap]:
        for owner, edge_list in edges.items():
            edge_css = self.get_css(owner, ElkEdge, edge_style)
            port_css = self.get_css(owner, ElkPort, port_style)
            layout_options = self.get_layout(owner, ElkEdge)
            for edge in edge_list:
                elknode = nodes[owner]
                if elknode.edges is None:
                    elknode.edges = []
                if edge.source_port is not None:
                    source_var = (edge.source, edge.source_port)
                    if source_var not in ports:
                        port = await self.make_port(
                            edge.source, edge.source_port, port_css
                        )
                        ports[port.elkport.id] = port
                if edge.target_port is not None:
                    target_var = (edge.target, edge.target_port)
                    if target_var not in ports:
                        port = await self.make_port(
                            edge.target, edge.target_port, port_css
                        )
                        ports[port.elkport.id] = port

                elknode.edges += [await self.make_edge(edge, edge_css, layout_options)]
        return nodes, ports

    async def make_edge(
        self, edge: Edge, styles: Optional[Set[str]] = None, layout_options: Dict = None
    ) -> ElkExtendedEdge:
        """Make the associated Elk edge for the given Edge

        :param edge: Edge object to wrap
        :type edge: Edge
        :param styles: List of css classes to add to given Elk edge, defaults to None
        :type styles: Optional[List[str]], optional
        :return: Elk edge
        :rtype: ElkExtendedEdge
        """
        properties = None
        if styles:
            properties = dict(cssClasses=" ".join(styles))

        labels = []
        for i, label in enumerate(edge.data.get(self.label_key, [])):
            layout_options = self.get_layout(
                edge.owner, ElkLabel
            )  # TODO add edgelabel type?
            if isinstance(label, ElkLabel):
                label = label.to_dict()  # used to create copy of label
            if isinstance(label, dict):
                label = ElkLabel.from_dict(label)
            if isinstance(label, str):
                label = ElkLabel(id=f"{edge.owner}_label_{i}_{label}", text=label)
            label.layoutOptions = merge(label.layoutOptions, layout_options)
            # TODO size the labels in bulk
            await self.size_labels([label])
            labels.append(label)
        for label in labels:
            self.register(label, edge)
        elk_edge = ElkExtendedEdge(
            id=self.edge_id(edge),
            sources=[self.port_id(edge.source, edge.source_port)],
            targets=[self.port_id(edge.target, edge.target_port)],
            properties=properties,
            layoutOptions=self.get_layout(edge.owner, ElkEdge),
            labels=compact(labels),
        )
        self.register(elk_edge, edge)
        return elk_edge

    async def make_port(
        self, owner: Hashable, port: Hashable, styles: Optional[Set[str]] = None
    ) -> Port:
        """Make the associated elk port for the given owner node and port

        :param owner: [description]
        :type owner: Hashable
        :param port: [description]
        :type port: Hashable
        :param styles: list of css classes to apply to given ElkPort
        :type styles: List[str]
        :return: [description]
        :rtype: ElkPort
        """
        # Test if elk port has already been created
        port_id = self.port_id(owner, port)
        port = self._ports.get(port_id, None)
        if port:
            return port

        properties = None
        if styles:
            properties = dict(cssClasses=" ".join(styles))

        # TODO labels
        self.get_node_data(owner).get(self.port_key, {})
        # todo ports a list or a dict?

        elk_port = ElkPort(
            id=port_id,
            height=self.port_scale,
            width=self.port_scale,
            properties=properties,
        )
        port = Port(node=owner, elkport=elk_port)
        self._ports[port_id] = port
        return port

    def register(self, element: ElkGraphElement, item: Hashable) -> str:
        """Register Elk Element as a way to find the particular item.

        This method is used in the `lookup` method for dereferencing the elk id.

        :param element: [description]
        :type element: ElkGraphElement
        :param item: [description]
        :type item: Hashable
        """

        self._elk_to_item[element.id] = item
        self._item_to_elk[item] = element.id
        return element

    async def size_labels(self, labels: List[ElkLabel]):
        """Run a list of ElkLabels through to the TextSizer measurer

        :param labels: [description]
        :type labels: List[ElkLabel]
        :return: Updated Labels
        """
        if self.text_sizer is not None:
            sizes = await self.text_sizer.measure(tuple(labels))
        else:
            sizes = [
                TextSize(
                    width=10 * len(label.text),
                    height=10,  # TODO add height default
                )
                for label in labels
            ]

        for size, label in zip(sizes, labels):
            label.width = size.width
            label.height = size.height

    def get_node_data(self, node: Hashable) -> Dict:
        g, tree = self.source
        return g.nodes.get(node, {})

    async def collect_ports(self, *nodes) -> PortMap:
        ports: PortMap = {}
        for node in nodes:
            values = self.get_node_data(node).get(self.port_key, [])
            for i, port in enumerate(values):
                if isinstance(port, ElkPort):
                    # generate a fresh copy of the port to prevent mutating original
                    port = port.to_dict()
                elif isinstance(port, str):
                    port_id = self.port_id(node, port)
                    port = {
                        "id": port_id,
                        "labels": [
                            {
                                "text": port,
                                "id": f"{port}_label_{i}",
                            }
                        ],
                    }

                if isinstance(port, dict):
                    elkport = ElkPort.from_dict(port)

                if elkport.width is None:
                    elkport.width = self.port_scale
                if elkport.height is None:
                    elkport.height = self.port_scale
                ports[elkport.id] = Port(node=node, elkport=elkport)
        return ports

    def collect_labels(self, nodes: NodeMap) -> Tuple[ElkLabel]:
        """Iterate over the map of ElkNodes and pluck labels from:
            * node
            * node.ports
            * node.edges

        :param nodes: [description]
        :type nodes: NodeMap
        :return: [description]
        :rtype: Tuple[ElkLabel]
        """
        labels = []
        for elknode in nodes.values():
            for label in listed(elknode.labels):
                labels.append(label)
            for elkport in listed(elknode.ports):
                for label in listed(elkport.labels):
                    labels.append(label)
            for elkedge in listed(elknode.edges):
                for label in listed(elkedge.labels):
                    labels.append(label)
        return tuple(labels)

    async def make_labels(self, node: Hashable) -> Optional[List[ElkLabel]]:
        labels = []
        css = self.get_css(node, ElkLabel)
        properties = None
        g, tree = self.source
        data = g.nodes.get(node, {})
        values = data.get(self.label_key, [data.get("_id", f"{node}")])

        if css:
            properties = dict(cssClasses=" ".join(css))

        if isinstance(values, (str, ElkLabel)):
            values = [values]
        # get node labels
        for i, label in enumerate(values):
            if isinstance(label, str):
                label = ElkLabel(
                    id=f"{label}_label_{i}_{node}",
                    text=label,
                )
            elif isinstance(label, ElkLabel):
                # prevent mutating original label in the node data
                label = label.to_dict()
            if isinstance(label, dict):
                label = ElkLabel(**label)

            # add css classes and layout options
            label.layoutOptions = merge(
                label.layoutOptions, self.get_layout(node, ElkLabel)
            )
            label.properties = merge(label.properties, properties)

            labels.append(label)
            self.register(label, node)
        return labels

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
        )  # will index edges by nx.lowest_common_ancestor
        hidden: EdgeMap = defaultdict(
            list
        )  # will index edges by nx.lowest_common_ancestor
        g, tree = self.source
        attr = self.HIDDEN_ATTR
        hidden: List[Tuple[List, List]] = []

        visible: EdgeMap = defaultdict(
            list
        )  # will index edges by nx.lowest_common_ancestor
        hidden: EdgeMap = defaultdict(
            list
        )  # will index edges by nx.lowest_common_ancestor

        for source, target, edge_data in g.edges(data=True):
            shidden = is_hidden(tree, source, attr)
            thidden = is_hidden(tree, target, attr)

            source_port, target_port = get_ports(edge_data)

            if shidden or thidden:
                try:
                    vis_source = self.closest_visible(source)
                    vis_target = self.closest_visible(target)
                    owner = self.closest_common_visible((vis_source, vis_target))

                    # create new slack ports if source or target is remapped
                    if vis_source != source:
                        source_port = (source, source_port)
                    if vis_target != target:
                        target_port = (target, target_port)
                except ValueError:
                    continue  # bail if no possible target or source
                if vis_source != vis_target:
                    hidden[owner].append(
                        Edge(
                            source=vis_source,
                            source_port=source_port,
                            target=vis_target,
                            target_port=target_port,
                            data=edge_data,
                            owner=owner,
                        )
                    )
            else:
                owner = self.closest_common_visible((source, target))
                visible[owner].append(
                    Edge(
                        source=source,
                        source_port=source_port,
                        target=target,
                        target_port=target_port,
                        data=edge_data,
                        owner=owner,
                    )
                )
        return visible, hidden

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
            return ElkRoot
        result = lowest_common_ancestor(tree, [self.closest_visible(n) for n in nodes])
        return result

    def from_id(self, element_id: str) -> Hashable:
        """Use the elk identifiers to find original objects"""
        try:
            return self._elk_to_item[element_id]
        except KeyError:
            raise ValueError(f"Element id `{element_id}` not in elk id registry.")

    def to_id(self, item: Hashable) -> str:
        """Use original objects to find elk id"""
        try:
            return self._item_to_elk[item]
        except KeyError:
            raise ValueError(f"Item `{item}` not in elk id registry.")


def is_hidden(tree: nx.DiGraph, node: Hashable, attr: str) -> bool:
    """Iterate  on the node ancestors and determine if it is hidden along the chain"""
    if tree is not None and node in tree:
        if tree.nodes[node].get(attr, False):
            return True
        for ancestor in nx.ancestors(tree, node):
            if tree.nodes[ancestor].get(attr, False):
                return True
    return False


def merge(d1: Optional[Dict], d2: Optional[Dict]) -> Optional[Dict]:
    """Merge two dictionaries while first testing if either are `None`.
    The first dictionary's keys take precedence over the second dictionary.
    If the final merged dictionary is empty `None` is returned.

    :param d1: primary dictionary
    :type d1: Optional[Dict]
    :param d2: secondary dictionary
    :type d2: Optional[Dict]
    :return: merged dictionary
    :rtype: Dict
    """
    if d1 is None:
        d1 = {}
    if d2 is None:
        d2 = {}
    value = {**d2, **d1}  # right most wins if duplicated keys
    if value:
        return value


def listed(values: Optional[List]) -> List:
    """Checks if incoming `values` is None then either returns a new list or
    original value.

    :param values: List of values
    :type values: Optional[List]
    :return: List of values or empty list
    :rtype: List
    """
    if values is None:
        return []
    return values
