# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from collections import defaultdict
from functools import lru_cache
from typing import Dict, Hashable, List, Optional, Set, Tuple, Type, Union

import networkx as nx
import traitlets as T

import ipyelk.diagram.layout_options as opt

from .. import elements
from ..diagram.elk_model import (
    ElkEdge,
    ElkExtendedEdge,
    ElkGraphElement,
    ElkLabel,
    ElkNode,
    ElkPort,
    ElkProperties,
    ElkRoot,
)
from ..transform import Edge, EdgeMap, ElkTransformer, NodeMap, Port, PortMap
from ..util import merge
from .nx import (
    build_hierarchy,
    compact,
    get_ports,
    is_hidden,
    lowest_common_ancestor,
    map_visible,
)


class XELK(ElkTransformer):
    """NetworkX source graphs to a valid ELK JSON dictionary structure

    :param source: Tuple of NetworkX graphs. The first graph contains
    node/port/edge information while the second graph contains the node
    hierarchy.

    :param value: Output elk json

    """

    HIDDEN_ATTR = "hidden"
    hoist_hidden_edges: bool = True

    source: Tuple[nx.Graph, nx.DiGraph] = T.Tuple(
        T.Instance(nx.Graph), T.Instance(nx.DiGraph, allow_none=True)
    )
    layouts = T.Dict()  # keys: NetworkX nodes {ElkElements: {layout options}}
    css_classes = T.Dict()

    port_scale = T.Int(default_value=5)
    label_key = T.Unicode(default_value="labels")
    port_key = T.Unicode(default_value="ports")

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
        :return: Element ID
        """
        g, tree = self.source
        if node is ElkRoot:
            return self.ELK_ROOT_ID
        elif node in g:
            mark, data = self.get_node_data(node)
            return data.get("id", f"{node}")
        return f"{node}"

    def port_id(self, node: Hashable, port: Optional[Hashable] = None) -> str:
        """Get a suitable Elk identifier from the node and port

        :param node: Node from the incoming NetworkX graph
        :param port: Port identifier, defaults to None
        :return: If no port is provided will refer to the node
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

    async def transform(self) -> ElkNode:
        """Generate ELK dictionary structure
        :return: Root Elk node
        """
        # TODO decide behavior for nodes that exist in the tree but not g
        g, tree = self.source
        self.clear_registry()
        visible_edges, hidden_edges = self.collect_edges()

        # Process visible NetworkX nodes into elknodes
        visible_nodes = [
            n for n in g.nodes() if not is_hidden(tree, n, self.HIDDEN_ATTR)
        ]

        # make elknodes then connect their hierarchy
        elknodes: NodeMap = {}
        ports: PortMap = {}
        for node in visible_nodes:
            elknode, node_ports = await self.make_elknode(node)
            for key, value in node_ports.items():
                ports[key] = value
            elknodes[node] = elknode

        # make top level ElkNode and attach all others as children
        elknodes[ElkRoot] = top = ElkNode(
            id=self.ELK_ROOT_ID,
            children=build_hierarchy(g, tree, elknodes, self.HIDDEN_ATTR),
            layoutOptions=self.get_layout(ElkRoot, "parents"),
        )

        # map of original nodes to the generated elknodes
        for node, elk_node in elknodes.items():
            self.register(elk_node, node)

        elknodes, ports = await self.process_edges(elknodes, ports, visible_edges)
        # process edges with one or both original endpoints are hidden
        if self.hoist_hidden_edges:
            elknodes, ports = await self.process_edges(
                elknodes,
                ports,
                hidden_edges,
                edge_style={"slack-edge"},
                port_style={"slack-port"},
            )

        # iterate through the port map and add ports to ElkNodes
        for port_id, port in ports.items():
            owner = port.node
            elkport = port.elkport
            if owner not in elknodes:
                # TODO skip generating port to begin with
                break
            elknode = elknodes[owner]
            if elknode.ports is None:
                elknode.ports = []
            layout = self.get_layout(owner, ElkPort)
            elkport.layoutOptions = merge(elkport.layoutOptions, layout)
            elknode.ports += [elkport]

            # map of ports to the generated elkports
            mark = port if port.mark is None else port.mark
            self.register(elkport, mark)
        return top

    async def make_elknode(self, node: Hashable) -> Tuple[ElkNode, PortMap]:
        """Get the elknode and ports associated with given NetworkX node

        :param node: Incoming NetworkX node
        :return: ElkNode and Ports
        """
        # merge layout options defined on the node data with default layout
        # options
        mark, node_data = self.get_node_data(node)
        layout = merge(
            node_data.get("layoutOptions", {}),
            self.get_layout(node, ElkNode),
        )
        labels = await self.make_labels(node)

        # update port map with declared ports in the NetworkX node data
        node_ports = await self.collect_ports(node)

        properties = self.get_properties(node, self.get_css(node, ElkNode)) or None

        elk_node = ElkNode(
            id=self.node_id(node),
            labels=labels,
            layoutOptions=layout,
            properties=properties,
            width=node_data.get("width", None),
            height=node_data.get("height", None),
        )
        return elk_node, node_ports

    def get_layout(
        self, node: Hashable, elk_type: Type[ElkGraphElement]
    ) -> Optional[Dict]:
        """Get the Elk Layout Options appropriate for given NetworkX node and
        filter by given elk_type

        :param node: NetworkX node
        :param elk_type: Elk Graph Element to apply layouts to
        :return: Dictionary of relevant layout options
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

        :param element: NetworkX node or edge
        :param dom_classes: Set of base CSS DOM classes to merge, defaults to
        Set[str]=None
        :return: Set of CSS Classes to apply
        """

        g, tree = self.source

        properties = []

        if g and element in g:
            mark, data = self.get_node_data(element)
            g_props = data.get("properties", {})
            if g_props:
                properties += [g_props]
        if hasattr(element, "data"):
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
        """Get the CSS Classes appropriate for given NetworkX node given
        elk_type

        :param node: NetworkX node
        :param elk_type: ElkGraphElement to get appropriate css classes
        :param dom_classes: Set of base CSS DOM classes to merge, defaults to
        Set[str]=None
        :return: Set of CSS Classes to apply
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
            for edge in edge_list:
                elknode = nodes[owner]
                if elknode.edges is None:
                    elknode.edges = []
                if edge.source_port is not None:
                    port_id = self.port_id(edge.source, edge.source_port)
                    if port_id not in ports:
                        ports[port_id] = await self.make_port(
                            edge.source, edge.source_port, port_css
                        )
                if edge.target_port is not None:
                    port_id = self.port_id(edge.target, edge.target_port)
                    if port_id not in ports:
                        ports[port_id] = await self.make_port(
                            edge.target, edge.target_port, port_css
                        )

                elknode.edges += [await self.make_edge(edge, edge_css)]
        return nodes, ports

    async def make_edge(
        self, edge: Edge, styles: Optional[Set[str]] = None
    ) -> ElkExtendedEdge:
        """Make the associated Elk edge for the given Edge

        :param edge: Edge object to wrap
        :param styles: List of css classes to add to given Elk edge, defaults to None
        :return: Elk edge
        """

        labels = []
        properties = self.get_properties(edge, styles) or None
        label_layout_options = self.get_layout(
            edge.owner, ElkLabel
        )  # TODO add edgelabel type?
        edge_layout_options = self.get_layout(edge.owner, ElkEdge)

        for i, label in enumerate(edge.data.get(self.label_key, [])):

            if isinstance(label, ElkLabel):
                label = label.to_dict()  # used to create copy of label
            if isinstance(label, dict):
                label = ElkLabel.from_dict(label)
            if isinstance(label, str):
                label = ElkLabel(id=f"{edge.owner}_label_{i}_{label}", text=label)
            label.layoutOptions = merge(label.layoutOptions, label_layout_options)
            labels.append(label)
        mark = edge if edge.mark is None else edge.mark
        for label in labels:
            self.register(label, mark)
        elk_edge = ElkExtendedEdge(
            id=edge.data.get("id", self.edge_id(edge)),
            sources=[self.port_id(edge.source, edge.source_port)],
            targets=[self.port_id(edge.target, edge.target_port)],
            properties=properties,
            layoutOptions=merge(edge.data.get("layoutOptions"), edge_layout_options),
            labels=compact(labels),
        )
        self.register(elk_edge, mark)
        return elk_edge

    async def make_port(
        self, owner: Hashable, port: Hashable, styles: Optional[Set[str]] = None
    ) -> Port:
        """Make the associated elk port for the given owner node and port

        :param owner: NetworkX node
        :param port: NetworkX port name
        :param styles: list of css classes to apply to given ElkPort
        :return: Elk port
        """
        port_id = self.port_id(owner, port)
        properties = self.get_properties(port, styles) or None

        elk_port = ElkPort(
            id=port_id,
            height=self.port_scale,
            width=self.port_scale,
            properties=properties,
            # TODO labels
        )
        return Port(node=owner, elkport=elk_port)

    def get_node_data(self, node: Hashable) -> Tuple[Optional[elements.Mark], Dict]:
        g = self.source[0]
        data = g.nodes.get(node, {})
        return split_mark_data(data)

    async def collect_ports(self, *nodes) -> PortMap:
        """Get port map for list of incoming NetworkX nodes

        :return: ElkPort objects mapped to their
        """
        ports: PortMap = {}
        for node in nodes:
            port_list = get_port_list(node)

            node_mark, data = self.get_node_data(node)
            values = data.get(self.port_key, [])
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

                if i <= len(port_list):
                    port_mark = elements.Mark(element=port_list[i], context=node.context)
                else:
                    port_mark = node_mark
                ports[elkport.id] = Port(node=node, elkport=elkport, mark=port_mark)
        return ports

    async def make_labels(self, node: Hashable) -> List[ElkLabel]:
        """Get associated ElkLabels for a given input NetworkX node.

        :param node: Input NetworkX node
        :return: List of ElkLabels
        """
        labels = []
        mark, data = self.get_node_data(node)
        values = data.get(self.label_key, [data.get("_id", f"{node}")])

        properties = {}
        css_classes = self.get_css(node, ElkLabel)
        if css_classes:
            properties["cssClasses"] = " ".join(css_classes)

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
                label = ElkLabel.from_dict(label)

            # add css classes and layout options
            label.layoutOptions = merge(
                label.layoutOptions, self.get_layout(node, ElkLabel)
            )
            merged_props = merge(label.properties, properties)
            if merged_props is not None:
                merged_props = ElkProperties.from_dict(merged_props)
            label.properties = merged_props

            labels.append(label)

            lmark = node

            # test if the label mark is selectable independently
            if isinstance(mark, elements.Mark):
                el = mark.element.labels[i]
                if el.selectable:
                    lmark = elements.Mark(element=el, context=mark.context)
            print(label.id)
            self.register(label, lmark)
        return labels

    def collect_edges(self) -> Tuple[EdgeMap, EdgeMap]:
        """Method to process edges in the NetworkX source graph and separate
        visible edges and hidden edges.

        :return: Visible edge mapping and hidden edge mapping.
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

        closest_visible = map_visible(g, tree, attr)

        @lru_cache()
        def closest_common_visible(nodes: Tuple[Hashable]) -> Hashable:
            if tree is None:
                return ElkRoot
            result = lowest_common_ancestor(tree, nodes)
            return result

        for source, target, edge_data in g.edges(data=True):
            mark, edge_data = split_mark_data(edge_data)
            source_port, target_port = get_ports(edge_data)
            vis_source = closest_visible[source]
            vis_target = closest_visible[target]
            shidden = vis_source != source
            thidden = vis_target != target
            owner = closest_common_visible((vis_source, vis_target))
            if source == target and source == owner:
                if owner in tree:
                    for p in tree.predecessors(owner):
                        # need to make this edge's owner to it's parent
                        owner = p

            if shidden or thidden:
                # create new slack ports if source or target is remapped
                if vis_source != source:
                    source_port = (source, source_port)
                if vis_target != target:
                    target_port = (target, target_port)

                if vis_source != vis_target:
                    hidden[owner].append(
                        Edge(
                            source=vis_source,
                            source_port=source_port,
                            target=vis_target,
                            target_port=target_port,
                            data=edge_data,
                            mark=mark,
                            owner=owner,
                        )
                    )
            else:
                visible[owner].append(
                    Edge(
                        source=source,
                        source_port=source_port,
                        target=target,
                        target_port=target_port,
                        data=edge_data,
                        mark=mark,
                        owner=owner,
                    )
                )
        return visible, hidden


def split_mark_data(data: Dict) -> Tuple[Optional[elements.Mark], Dict]:
    mark = data.get("mark", None)
    if isinstance(mark, elements.Mark):
        if "elkjson" not in data:
            data["elkjson"] = mark.to_json()
        return mark, data["elkjson"]
    return mark, data


def get_port_list(node)->List[elements.Port]:
    if isinstance(node, elements.Mark):
        return list(node.element.ports.values())
    return []