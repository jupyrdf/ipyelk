# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from collections import defaultdict
from functools import lru_cache
from typing import Dict, Hashable, List, Optional, Set, Tuple, Type, Union

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
from ..diagram.elk_text_sizer import ElkTextSizer, size_labels
from ..transform import (
    Edge,
    EdgeMap,
    ElkTransformer,
    NodeMap,
    Port,
    PortMap,
    collect_labels,
    merge,
)
from .nx import build_hierarchy, compact, get_ports, is_hidden, lowest_common_ancestor


class XELK(ElkTransformer):
    """NetworkX DiGraphs to ELK dictionary structure"""

    HIDDEN_ATTR = "hidden"
    ELK_ROOT_ID = "root"

    _hidden_edges: Optional[EdgeMap] = None
    _visible_edges: Optional[EdgeMap] = None

    source = T.Tuple(T.Instance(nx.Graph), T.Instance(nx.DiGraph, allow_none=True))
    layouts = T.Dict()  # keys: networkx nodes {ElkElements: {layout options}}
    css_classes = T.Dict()

    port_scale = T.Int(default_value=5)
    label_key = T.Unicode(default_value="labels")
    port_key = T.Unicode(default_value="ports")

    @T.default("source")
    def _default_source(self):
        return (nx.Graph(), None)

    @T.default("text_sizer")
    def _default_text_sizer(self):
        return ElkTextSizer()

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
        return "{}__{}___{}__{}".format(
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

        # make elknodes then connect their hierarchy
        elknodes = {node: await self.make_elknode(node) for node in visible_nodes}
        elknodes[ElkRoot] = top = ElkNode(
            id=self.ELK_ROOT_ID,
            children=build_hierarchy(g, tree, elknodes, self.HIDDEN_ATTR),
            layoutOptions=self.get_layout(ElkRoot, "parents"),
        )

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
        await size_labels(self.text_sizer, collect_labels([top]))
        # link children to parents
        self._nodes = elknodes

        for node, elk_node in elknodes.items():
            self.register(elk_node, node)
        return top

    async def make_elknode(self, node) -> ElkNode:
        # merge layout options defined on the node data with default layout options
        layout = merge(
            self.get_node_data(node).get("layoutOptions", {}),
            self.get_layout(node, ElkNode),
        )
        labels = await self.make_labels(node)

        # update port map with declared ports in the networkx node data
        node_ports = await self.collect_ports(node)
        for key, value in node_ports.items():
            self._ports[key] = value

        properties = self.get_properties(node, self.get_css(node, ElkNode)) or None

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

    def get_properties(
        self,
        element: Optional[Union[Hashable, str]],
        dom_classes: Optional[Set[str]] = None,
    ) -> Dict:
        """Get the properties for a graph element

        :param element: Networkx node or edge
        :type node: Hashable
        :param dom_classes: Set of base CSS DOM classes to merge, defaults to
        Set[str]=None
        :type dom_classes: [type], optional
        :return: Set of CSS Classes to apply
        :rtype: Set[str]
        """

        g, tree = self.source

        properties = []

        if isinstance(element, str):
            if g and element in g:
                g_props = g.nodes[element].get("properties", {})
                if g_props:
                    properties += [g_props]
        elif hasattr(element, "data"):
            properties += [element.data.get("properties", {})]
        elif isinstance(element, dict):
            properties += [element.get("properties", {})]

        if dom_classes:
            properties += [{"cssClasses": " ".join(dom_classes)}]

        if not properties:
            return {}
        elif len(properties) == 1:
            return properties[0]

        merged_properties = {}

        for props in properties[::-1]:
            merged_properties = merge(props, merged_properties)

        return merged_properties

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

        labels = []
        properties = self.get_properties(edge, styles) or None

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

        # TODO labels
        self.get_node_data(owner).get(self.port_key, {})
        # todo ports a list or a dict?

        properties = self.get_properties(port, styles) or None

        elk_port = ElkPort(
            id=port_id,
            height=self.port_scale,
            width=self.port_scale,
            properties=properties,
        )
        port = Port(node=owner, elkport=elk_port)
        self._ports[port_id] = port
        return port

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

    async def make_labels(self, node: Hashable) -> Optional[List[ElkLabel]]:
        labels = []
        g = self.source[0]
        data = g.nodes.get(node, {})
        values = data.get(self.label_key, [data.get("_id", f"{node}")])

        properties = self.get_properties(node, self.get_css(node, ElkLabel))

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
            return node
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
