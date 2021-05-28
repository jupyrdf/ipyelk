# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from collections import defaultdict
from typing import Dict, Iterator, List, Mapping, Optional, Set, Tuple, Type

import networkx as nx
from pydantic import BaseModel, Field

from ..exceptions import NotFoundError
from .common import EMPTY_SENTINEL
from .elements import BaseElement, Edge, HierarchicalElement, Label, Node, Port


class IDReport(BaseModel):
    duplicated: Dict[str, List[BaseElement]] = Field(
        default_factory=dict, description="Mapping of elements with a non unique id"
    )
    null_ids: List[BaseElement] = Field(
        default_factory=list, description="Elements without an id"
    )

    class Config:
        copy_on_model_validation = False

    def __bool__(self):
        return len(self.duplicated) + len(self.null_ids) > 0

    def message(self):
        msg = []
        if self.duplicated:
            msg.append("duplicated ids:")
            [msg.append("\t{eid}") for eid in self.duplicated.keys()]
        if self.null_ids:
            msg.append("elements missing an id:")
            [msg.append("\t{el}") for el in self.null_ids]
        return "\n".join(msg)


class EdgeReport(BaseModel):
    orphans: Set[Node] = Field(
        default_factory=set,
        description=(
            "elements that are referenced in an edge but not in the element hierarchy"
        ),
    )
    lca_mismatch: Dict[Edge, Tuple[Node, Optional[Node]]] = Field(
        default_factory=dict,
        description="edges that have a mismatched lowest common ancestor",
    )

    class Config:
        copy_on_model_validation = False


class VisIndex(BaseModel):
    class Config:
        copy_on_model_validation = False

    hidden: Dict[str, BaseElement] = Field(
        default_factory=dict,
        description=("mapping of old visabile elements ids to old elements"),
    )
    last_visible: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "mapping of old visabile element ids to it's closest visible ancestor id"
        ),
    )

    slack_edge_style: Set[str] = Field({"slack-edge"})
    slack_port_style: Set[str] = Field({"slack-port"})

    @classmethod
    def from_els(cls, *els: BaseElement) -> "VisIndex":
        index = {}
        last_visible = {}

        for el, is_hidden, last in iter_visible(*els):
            if is_hidden:
                el_id = el.get_id()
                index[el_id] = el
                last_visible[el_id] = last.get_id()
        return cls(
            hidden=index,
            last_visible=last_visible,
        )

    def get(self, key) -> Tuple[HierarchicalElement, str]:
        return self.hidden.get(key), self.last_visible.get(key)

    def __len__(self):
        return len(self.hidden)

    def port_factory(self, **kwargs) -> Port:
        port = Port(**kwargs)
        if port.width is None:
            port.width = 5
        if port.height is None:
            port.height = 5
        port.add_class(*self.slack_port_style)
        return port

    def edge_factory(self, *, slack_edge=False, **kwargs) -> Edge:
        edge = Edge(**kwargs)
        if slack_edge:
            edge.add_class(*self.slack_edge_style)
        return edge

    def clear_slack(self, *elements: BaseElement):
        for el in iter_elements(*elements):
            if isinstance(el, Port):
                el.remove_class(*self.slack_port_style)
            elif isinstance(el, Edge):
                el.remove_class(*self.slack_edge_style)


class ElementIndex(BaseModel):
    elements: Mapping[str, BaseElement] = Field(default_factory=dict)

    class Config:
        copy_on_model_validation = False

    def get(self, key: str) -> BaseElement:
        key = str(key)
        try:
            if key in self.elements:
                return self.elements[key]
            # make slack port / tag edge as slack as well...
            return self.elements[key]
        except KeyError as err:
            raise NotFoundError(f"Element with id:{key} not in index") from err

    def __getitem__(self, key):
        return self.get(key)

    def items(self) -> Iterator[Tuple[str, BaseElement]]:
        for key, value in self.elements.items():
            yield key, value

    @classmethod
    def from_els(cls, *els: BaseElement) -> "ElementIndex":

        elements = {el.get_id(): el for el in iter_elements(*els)}
        return cls(
            elements=elements,
        )

    def iter_types(self, *types):
        for key, value in self.items():
            if isinstance(value, types):
                yield key, value

    def nodes(self) -> Iterator[Tuple[str, Node]]:
        yield from self.iter_types(Node)

    def edges(
        self,
        source: HierarchicalElement = EMPTY_SENTINEL,
        target: HierarchicalElement = EMPTY_SENTINEL,
    ) -> Iterator[Tuple[str, Edge]]:
        for key, edge in self.iter_types(Edge):
            if source is not EMPTY_SENTINEL and edge.source is not source:
                continue
            if target is not EMPTY_SENTINEL and edge.target is not target:
                continue
            yield key, edge

    def labels(self) -> Iterator[Tuple[str, Label]]:
        yield from self.iter_types(Label)

    def ports(self) -> Iterator[Tuple[str, Port]]:
        yield from self.iter_types(Port)

    def root(self) -> Node:
        roots = []
        for key, node in self.nodes():
            if not node._parent:
                roots.append(node)
        # TODO handle multiple roots by making one higher level root?
        assert len(roots) == 1, "Multiple roots"
        return roots[0]

    def update(self, other: "ElementIndex"):
        fields = [
            "properties",
            "layoutOptions",
            "x",
            "y",
            "width",
            "height",
            "sections",
            "text",
        ]
        for key, e2 in other.items():
            e1 = self.get(key)
            if type(e1) == type(e2):
                for field in fields:
                    if hasattr(e1, field) and hasattr(e2, field):
                        setattr(e1, field, getattr(e2, field))

    def check_ids(self, *els) -> IDReport:
        ids = {}
        duplicated: Dict[str, List[BaseElement]] = defaultdict(list)
        null_ids: List[BaseElement] = []

        for el in iter_elements(self.root(), *els):
            if el.id is None:
                null_ids.append(el)
                continue
            eid = el.get_id()
            if eid in ids:
                duplicated[eid].append(el)
            else:
                ids[eid] = el

        for eid, value in duplicated.items():
            value.append(ids[eid])

        return IDReport(
            duplicated=duplicated,
            null_ids=null_ids,
        )

    def check_edges(self) -> EdgeReport:
        from ..loaders.nx.nxutils import get_owner

        orphans: Set[Node] = set()
        lca_mismatch: Dict[Edge, Tuple[Node, Node]] = {}

        root = self.root()

        # build orphaned set of nodes
        for el, edge in iter_edges(root):
            for endpt in (edge.source, edge.target):
                if endpt.get_id() not in self.elements:

                    # get the top ancestor of endpt and add to the orphan set
                    ancestor = get_ancestor(endpt)
                    assert isinstance(ancestor, Node)
                    orphans.add(ancestor)

        # check
        hierarchy = nx.DiGraph()
        hierarchy.add_edges_from(iter_hierarchy(root, types=(HierarchicalElement,)))
        hierarchy.add_edges_from(
            iter_hierarchy(*orphans, root=root, types=(HierarchicalElement,))
        )
        el_map = HierarchicalIndex.from_els(root, *orphans)
        for el, edge in iter_edges(root, *orphans):
            if edge in lca_mismatch:
                # skip edge processing if associated with an orphaned node
                continue
            owner = get_owner(edge, hierarchy=hierarchy, el_map=el_map)
            if el is not owner:
                lca_mismatch[edge] = (el, owner)

        return EdgeReport(
            orphans=orphans,
            lca_mismatch=lca_mismatch,
        )


class HierarchicalIndex(ElementIndex):
    elements: Mapping[str, HierarchicalElement] = Field(default_factory=dict)
    vis_index: VisIndex = Field(default_factory=VisIndex)

    @classmethod
    def from_els(
        cls, *els: BaseElement, vis_index: Optional[VisIndex] = None
    ) -> "HierarchicalIndex":

        elements = {
            el.get_id(): el
            for el in iter_elements(*els)
            if isinstance(el, HierarchicalElement)
        }
        if vis_index is None:
            vis_index = VisIndex()
        return cls(
            elements=elements,
            vis_index=vis_index,
        )

    def link_edges(self, edges_map: Dict[str, Tuple[Dict]]):
        for node_id, edges in edges_map.items():
            node = self.get(node_id)
            assert isinstance(node, Node)
            result = []
            for e in edges:
                edge = self.build_edge(e)
                if edge:
                    result.append(edge)
            node.edges = result

    def build_edge(self, edge: Dict) -> Optional[Edge]:
        """Build the edge

        If the source and target are on the same Node don't return an edge

        :param edge: [description]
        :type edge: Dict
        :return: [description]
        :rtype: Optional[Edge]
        """
        source = edge.get("source")
        if source is None:
            source = edge["sources"][0]
        target = edge.get("target")
        if target is None:
            target = edge["targets"][0]

        slack_edge = False
        if self.is_null_edge(source, target):
            return None

        if self.is_hidden(source):
            source = self.make_port(source)
            slack_edge = True
        else:
            source = self.get(source)
        if self.is_hidden(target):
            target = self.make_port(target)
            slack_edge = True
        else:
            target = self.get(target)

        edge_dict = {**edge, "source": source, "target": target}
        return self.vis_index.edge_factory(**edge_dict, slack_edge=slack_edge)

    def make_port(self, key: str) -> Port:
        if self.vis_index is None:
            raise ValueError(
                "Cannot make a port without understanding of hidden elements"
            )
        # get old hidden element and the id of it's last visible ancestor
        hidden_el, last_visible_id = self.vis_index.get(key)
        node = self.get(last_visible_id)
        assert isinstance(node, Node)
        try:
            port = node.get_port(key)
        except NotFoundError:
            port = self.vis_index.port_factory(id=key)
            node.add_port(port, key=key)
        return port

    def is_hidden(self, key):
        return key not in self.elements

    def is_null_edge(self, source, target) -> bool:
        source_node = self.get_visible_node(source)
        target_node = self.get_visible_node(target)
        return source_node is target_node

    def get_visible_node(self, el_id: str) -> Node:
        """Gets the visible node associated with the given el_id

        :param key: element id
        :return: Closest Visible Node
        """
        if self.is_hidden(el_id) and self.vis_index:
            _, el_id = self.vis_index.get(el_id)
        element = self.get(el_id)
        if isinstance(element, Port):
            element = element._parent
        assert isinstance(element, Node)
        return element


def iter_elements(*els: BaseElement) -> Iterator[BaseElement]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param el: current element
    :yield: sub element
    """
    for el in set(els):
        yield el
        if isinstance(el, Node):
            yield from iter_elements(*el.children)
            yield from iter_elements(*el.ports)
            yield from iter_elements(*el.edges)
        yield from iter_elements(*el.labels)


def iter_visible(
    *els: BaseElement, hidden=False, last_visible=EMPTY_SENTINEL
) -> Iterator[Tuple[BaseElement, bool, BaseElement]]:
    """Iterate over BaseElements hierarchy and track hidden

    :param el: current element
    :param hidden: containing element is hidden
    :yield: sub element and hidden state
    """
    for el in els:
        hidden = bool(hidden or el.properties.hidden)
        if not hidden:
            last_visible = el
        yield el, hidden, last_visible
        if isinstance(el, Node):
            yield from iter_visible(
                *el.children, hidden=hidden, last_visible=last_visible
            )
            yield from iter_visible(*el.ports, hidden=hidden, last_visible=last_visible)
            yield from iter_visible(*el.edges, hidden=hidden, last_visible=last_visible)
        yield from iter_visible(*el.labels, hidden=hidden, last_visible=last_visible)


def iter_edges(*els: Node) -> Iterator[Tuple[Node, Edge]]:
    """Iterate over BaseElements that follow the `Node` hierarchy and return
    edges and their parent

    :param el: current element
    :yield: owning Node, Edge
    """
    for el in set(els):
        for edge in el.edges:
            yield el, edge
        yield from iter_edges(*el.children)


def iter_hierarchy(
    *els: BaseElement,
    root=EMPTY_SENTINEL,
    types: Tuple[Type[BaseElement]] = (BaseElement,),
) -> Iterator[Tuple[BaseElement, BaseElement]]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param el: current element
    :yield: sub element
    """
    for el in els:
        if root is not EMPTY_SENTINEL:
            if isinstance(el, types):
                yield root, el
        if isinstance(el, Node):
            yield from iter_hierarchy(*el.children, root=el, types=types)
            yield from iter_hierarchy(*el.ports, root=el)
            yield from iter_hierarchy(*el.edges, root=el)
        yield from iter_hierarchy(*el.labels, root=el)


def get_ancestor(element: HierarchicalElement) -> HierarchicalElement:
    parent = element.get_parent()
    if parent is None:
        return element
    else:
        return get_ancestor(parent)
