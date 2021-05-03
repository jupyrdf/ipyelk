# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict, Iterator, Optional, Set, Tuple

from pydantic import BaseModel, Field

from ..exceptions import NotFoundError
from .common import EMPTY_SENTINEL
from .elements import BaseElement, Edge, HierarchicalElement, Node, Port


class VisIndex(BaseModel):
    # mapping of old visabile elements ids to old elements
    hidden: Dict[str, BaseElement]
    # mapping of old visabile element ids to it's closest visible ancestor id
    last_visible: Dict[str, str]

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


class ElementIndex(BaseModel):
    elements: Dict[str, HierarchicalElement]
    vis_index: Optional[VisIndex]  # Dict[str, BaseElement]

    def get(self, key: str) -> HierarchicalElement:
        if key in self.elements:
            return self.elements[key]
        # make slack port / tag edge as slack as well...
        return self.elements[key]

    def __getitem__(self, key):
        return self.get(key)

    def items(self) -> Iterator[Tuple[str, HierarchicalElement]]:
        for key, value in self.elements.items():
            yield key, value

    @classmethod
    def from_els(
        cls, *els: BaseElement, vis_index: Optional[VisIndex] = None
    ) -> "ElementIndex":

        elements = {
            el.get_id(): el
            for el in iter_elements(*els)
            if isinstance(el, HierarchicalElement)
        }
        return cls(
            elements=elements,
            vis_index=vis_index,
        )

    def link_edges(self, edges_map: Dict[str, Tuple[Dict]]):
        for node_id, edges in edges_map.items():
            node = self.get(node_id)
            assert isinstance(node, Node)
            node.edges = [self.build_edge(e) for e in edges]

    def build_edge(self, edge: Dict) -> Edge:
        source = edge.get("source")
        if source is None:
            source = edge["sources"][0]
        target = edge.get("target")
        if target is None:
            target = edge["targets"][0]

        slack_edge = False
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
        edge = Edge(**edge_dict)
        if slack_edge and self.vis_index:
            [edge.add_class(c) for c in self.vis_index.slack_edge_style]
        return edge

    def make_port(self, key: str) -> Port:
        if self.vis_index is None:
            raise ValueError(
                "Cannot make a port without understanding of hidden elements"
            )
        # get old hidden element and the id of it's last visible ancestor
        hidden_el, last_visible_id = self.vis_index.get(key)
        node = self.get(last_visible_id)
        try:
            port = node.get_port(key)
        except NotFoundError:
            port = Port(id=key)
            for c in self.vis_index.slack_port_style:
                port.add_class(c)
            node.add_port(port, key=key)
        return port

    def is_hidden(self, key):
        return key not in self.elements


def iter_elements(*els: BaseElement) -> Iterator[BaseElement]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param el: current element
    :yield: sub element
    """
    for el in els:
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


def iter_hierarchy(
    *els: BaseElement, root=EMPTY_SENTINEL
) -> Iterator[Tuple[BaseElement, BaseElement]]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param el: current element
    :yield: sub element
    """
    for el in els:
        if root is not EMPTY_SENTINEL:
            yield root, el
        if isinstance(el, Node):
            yield from iter_hierarchy(*el.children, root=el)
            yield from iter_hierarchy(*el.ports, root=el)
            yield from iter_hierarchy(*el.edges, root=el)
        yield from iter_hierarchy(*el.labels, root=el)
