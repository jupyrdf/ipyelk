# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from pydantic import BaseModel, Field, SerializeAsAny

from ..exceptions import NotFoundError
from .common import EMPTY_SENTINEL
from .elements import BaseElement, Edge, HierarchicalElement, Label, Node, Port


def _missing_id(el: BaseElement, what: str = "element") -> ValueError:
    # type name only: an element repr recurses through its whole subtree
    return ValueError(
        f"Cannot index {what} without an id ({type(el).__name__}); "
        "set `id` or build the index inside a Registry context"
    )


class IDReport(BaseModel):
    duplicated: dict[str, list[SerializeAsAny[BaseElement]]] = Field(
        default_factory=dict,
        description="Mapping of elements with a non unique id",
    )
    null_ids: list[SerializeAsAny[BaseElement]] = Field(
        default_factory=list, description="Elements without an id"
    )

    def __bool__(self):
        return len(self.duplicated) + len(self.null_ids) > 0

    def message(self):
        msg = []
        if self.duplicated:
            msg.append("duplicated ids:")
            msg.extend(f"\t{eid}" for eid in self.duplicated.keys())
        if self.null_ids:
            msg.append("elements missing an id:")
            msg.extend(f"\t{el}" for el in self.null_ids)
        return "\n".join(msg)


class EdgeReport(BaseModel):
    orphans: set[Node] = Field(
        default_factory=set,
        description=(
            "elements that are referenced in an edge but not in the element hierarchy"
        ),
    )
    lca_mismatch: dict[Edge, tuple[Node, Node | None]] = Field(
        default_factory=dict,
        description="edges that have a mismatched lowest common ancestor",
    )


class VisIndex(BaseModel):
    hidden: dict[str, SerializeAsAny[BaseElement]] = Field(
        default_factory=dict,
        description=("mapping of old visabile elements ids to old elements"),
    )
    last_visible: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "mapping of old visabile element ids to it's closest visible ancestor id"
        ),
    )

    slack_edge_style: set[str] = Field({"slack-edge"})
    slack_port_style: set[str] = Field({"slack-port"})

    @classmethod
    def from_els(cls, *els: BaseElement) -> VisIndex:
        index = {}
        last_visible = {}

        for el, is_hidden, last in iter_visible(*els):
            if is_hidden:
                el_id = el.get_id()
                if el_id is None:
                    raise _missing_id(el)
                if not isinstance(last, BaseElement):
                    raise ValueError(
                        f"Cannot index hidden {type(el).__name__} {el_id!r} "
                        "without a visible ancestor"
                    )
                last_id = last.get_id()
                if last_id is None:
                    raise _missing_id(last, "visible ancestor")
                index[el_id] = el
                last_visible[el_id] = last_id
        return cls(
            hidden=index,
            last_visible=last_visible,
        )

    def get(self, key) -> tuple[BaseElement | None, str | None]:
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
    elements: dict[str, SerializeAsAny[BaseElement]] = Field(default_factory=dict)

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

    def items(self) -> Iterator[tuple[str, BaseElement]]:
        for key, value in self.elements.items():
            yield key, value

    @classmethod
    def from_els(cls, *els: BaseElement) -> ElementIndex:
        elements: dict[str, SerializeAsAny[BaseElement]] = {}
        for el in iter_elements(*els):
            el_id = el.get_id()
            if el_id is None:
                raise _missing_id(el)
            elements[el_id] = el
        return cls(
            elements=elements,
        )

    def iter_types(self, *types):
        for key, value in self.items():
            if isinstance(value, types):
                yield key, value

    def nodes(self) -> Iterator[tuple[str, Node]]:
        yield from self.iter_types(Node)

    def edges(
        self,
        source: HierarchicalElement | type = EMPTY_SENTINEL,
        target: HierarchicalElement | type = EMPTY_SENTINEL,
    ) -> Iterator[tuple[str, Edge]]:
        for key, edge in self.iter_types(Edge):
            if source is not EMPTY_SENTINEL and edge.source is not source:
                continue
            if target is not EMPTY_SENTINEL and edge.target is not target:
                continue
            yield key, edge

    def labels(self) -> Iterator[tuple[str, Label]]:
        yield from self.iter_types(Label)

    def ports(self) -> Iterator[tuple[str, Port]]:
        yield from self.iter_types(Port)

    def root(self) -> Node:
        roots = []
        for key, node in self.nodes():
            if not node._parent:
                roots.append(node)
        # TODO handle multiple roots by making one higher level root?
        assert len(roots) >= 1, "Multiple roots"
        root = roots[0]
        assert isinstance(root, Node), f"Root is not of type Node. Not {type(root)}."
        assert len(root.ports) == 0, (
            f"Root should not have any ports. Current root has `{len(root.ports)}`."
        )
        assert len(root.labels) == 0, (
            f"Root should not have any labels. Current root has `{len(root.labels)}`."
        )
        return root

    def update(self, other: ElementIndex):
        """Merge ``other`` into this index.

        Known ids are updated in place (element identity is preserved, which is
        what keeps `hidden` elements -- stripped from every serialized value by
        `Node.model_dump` -- alive across browser roundtrips); unknown ids are added,
        so elements that only exist in a value coming back from the browser
        (e.g. slack ports) become addressable without discarding the index.
        """
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
            e1 = self.elements.get(key)
            if e1 is None:
                self.elements[key] = e2
            elif type(e1) == type(e2):
                for field in fields:
                    if hasattr(e1, field) and hasattr(e2, field):
                        setattr(e1, field, getattr(e2, field))

    def check_ids(self, *els) -> IDReport:
        ids = {}
        duplicated: dict[str, list[BaseElement]] = defaultdict(list)
        null_ids: list[BaseElement] = []

        for el in iter_elements(self.root(), *els):
            if el.id is None:
                null_ids.append(el)
                continue
            eid = el.get_id()
            assert eid is not None
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

    @staticmethod
    def depths(root: Node, *orphans: Node) -> dict[int, int]:
        """Depth of every node under ``root``, keyed by ``id()``.

        ``orphans`` are nodes referenced by an edge but missing from the
        hierarchy; :meth:`check_edges` reasons about them as children of
        ``root`` -- which is what ``ValidationPipe.fix_orphans`` goes on to make
        true -- so they start at depth 1.

        Keys are ``id()`` and not element ids: this map is built and consumed
        within a single :meth:`check_edges` call, elements are not hashable by
        value, and an un-indexed element may not have an id yet.
        """
        depths: dict[int, int] = {id(root): 0}
        stack: list[tuple[Node, int]] = [(orphan, 1) for orphan in orphans]
        stack.extend((child, 1) for child in root.children)
        while stack:
            node, depth = stack.pop()
            key = id(node)
            if key in depths:
                continue
            depths[key] = depth
            stack.extend((child, depth + 1) for child in node.children)
        return depths

    @staticmethod
    def lca_by_parent(
        u: HierarchicalElement,
        v: HierarchicalElement,
        depths: dict[int, int],
        root: Node | None = None,
    ) -> Node | None:
        """Lowest common ancestor of two edge endpoints, by walking parents.

        Equivalent to ``nx.lowest_common_ancestor`` over the node hierarchy, but
        ``O(depth)`` per edge instead of ``O(N + E)``: ports resolve to their
        owning node, a self loop resolves to that node's parent, and otherwise
        the deeper endpoint is raised to the shallower one before both walk up
        together.

        ``depths`` comes from :meth:`depths`; ``root`` is the parent the same
        call adopted the orphans with, so an orphan's walk reaches it too.
        Returns ``None`` when the walk runs off the top of the hierarchy, which
        only a self loop on a parentless node can do.

        Ownership trusts the ``_parent`` links (``get_parent``), not
        ``children`` membership: an element appended to ``children`` without
        ``set_parent`` (``add_child`` does both) has no parent to walk up
        through and is reported as unreachable (:class:`NotFoundError`).
        """
        a: HierarchicalElement | None = u.get_parent() if isinstance(u, Port) else u
        b: HierarchicalElement | None = v.get_parent() if isinstance(v, Port) else v

        if a is b:
            # self loops need to be owned by their parent
            return None if a is None else a.get_parent()

        def up(node: HierarchicalElement | None) -> Node:
            parent = None if node is None else node.get_parent()
            if parent is None and node is not root and depths.get(id(node)):
                # an orphan root: `check_edges` hangs it off the hierarchy root
                parent = root
            if parent is None:
                raise NotFoundError(f"Unable to find {node} in the hierarchy")
            return parent

        for endpt in (a, b):
            if endpt is None or id(endpt) not in depths:
                raise NotFoundError(f"Unable to find {endpt} in the hierarchy")

        a_depth = depths[id(a)]
        b_depth = depths[id(b)]
        while a_depth > b_depth:
            a = up(a)
            a_depth -= 1
        while b_depth > a_depth:
            b = up(b)
            b_depth -= 1
        while a is not b:
            a = up(a)
            b = up(b)
        # ``a is not b`` on entry, so the meeting point came out of ``up``
        assert isinstance(a, Node)
        return a

    def check_edges(self) -> EdgeReport:
        """Check edges' endpoints for references to nodes outside of the current
        hierarchy as well as which edges should be remapped to the appropriate
        lowest common ancestor.

        Reachability is judged by the ``children`` walk (:meth:`depths`) and
        ownership by the ``_parent`` links (:meth:`lca_by_parent`), so a child
        appended to ``children`` without ``set_parent`` (use ``add_child``) is
        reported as unreachable rather than resolved through the hierarchy.
        """
        orphans: set[Node] = set()
        lca_mismatch: dict[Edge, tuple[Node, Node | None]] = {}

        root = self.root()

        # build orphaned set of nodes
        for el, edge in iter_edges(root):
            for endpt in (edge.source, edge.target):
                if endpt.get_id() not in self.elements:
                    # get the top ancestor of endpt and add to the orphan set
                    ancestor = get_ancestor(endpt)
                    assert isinstance(ancestor, Node)
                    orphans.add(ancestor)

        # check: one walk over the hierarchy pays for every edge's ancestor
        # lookup below
        depths = self.depths(root, *orphans)
        for el, edge in iter_edges(root, *orphans):
            if edge in lca_mismatch:
                # skip edge processing if associated with an orphaned node
                continue
            owner = self.lca_by_parent(edge.source, edge.target, depths, root=root)
            if owner is None:
                # a self loop on a parentless node: the previous implementation
                # resolved the `None` ancestor through the element map, so it
                # raised here too
                raise NotFoundError("Element with id:None not in index")
            assert isinstance(owner, Node)
            if el is not owner:
                lca_mismatch[edge] = (el, owner)
        return EdgeReport(
            orphans=orphans,
            lca_mismatch=lca_mismatch,
        )

    def get_reports(self) -> tuple[EdgeReport, IDReport]:
        edge_report = self.check_edges()
        id_report = self.check_ids(*edge_report.orphans)
        return edge_report, id_report


class HierarchicalIndex(ElementIndex):
    elements: dict[str, SerializeAsAny[BaseElement]] = Field(default_factory=dict)
    vis_index: VisIndex = Field(default_factory=VisIndex)

    @classmethod
    def from_els(
        cls, *els: BaseElement, vis_index: VisIndex | None = None
    ) -> HierarchicalIndex:
        elements: dict[str, SerializeAsAny[BaseElement]] = {}
        for el in iter_elements(*els):
            if isinstance(el, HierarchicalElement):
                el_id = el.get_id()
                if el_id is None:
                    raise _missing_id(el)
                elements[el_id] = el
        if vis_index is None:
            vis_index = VisIndex()
        return cls(
            elements=elements,
            vis_index=vis_index,
        )

    def link_edges(self, edges_map: dict[str, tuple[dict]]):
        for node_id, edges in edges_map.items():
            node = self.get(node_id)
            assert isinstance(node, Node)
            result = []
            for e in edges:
                edge = self.build_edge(e)
                if edge:
                    result.append(edge)
            node.edges = result

    def build_edge(self, edge: dict) -> Edge | None:
        """Build the edge

        If the source and target are on the same Node don't return an edge

        :param edge: [description]
        :type edge: dict
        :return: [description]
        :rtype: Edge | None
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
        _hidden_el, last_visible_id = self.vis_index.get(key)
        if last_visible_id is None:
            raise NotFoundError(f"Visible ancestor for {key} not found")
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
        source_node, source_hidden = self.get_visible_node(source)
        target_node, target_hidden = self.get_visible_node(target)
        # if either source or target are hidden check if mapped to same common ancestor
        if source_hidden or target_hidden:
            return source_node is target_node
        return False

    def get_visible_node(self, el_id: str) -> tuple[Node, bool]:
        """Gets the visible node associated with the given el_id

        :param key: element id
        :return: Closest Visible Node and if the original element was hidden
        """
        hidden = self.is_hidden(el_id)
        if hidden and self.vis_index:
            _, el_id = self.vis_index.get(el_id)
            if el_id is None:
                raise NotFoundError(f"Visible ancestor for {el_id} not found")
        element = self.get(el_id)
        if isinstance(element, Port):
            element = element._parent
        assert isinstance(element, Node)
        return element, hidden


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
) -> Iterator[tuple[BaseElement, bool, BaseElement]]:
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


def iter_edges(*els: Node) -> Iterator[tuple[Node, Edge]]:
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
    types: tuple[type[BaseElement], ...] = (BaseElement,),
) -> Iterator[tuple[BaseElement, BaseElement]]:
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


def iter_labels(
    *els: BaseElement,
) -> Iterator[tuple[Node, Label]]:
    """Iterate over BaseElements that follow the `Node` hierarchy

    :param els: iterable of elements
    :yield: element and label pair
    """
    for el in els:
        if isinstance(el, Node):
            yield from iter_labels(
                *el.children,
            )
        yield from zip([el], el.labels)


def get_ancestor(element: HierarchicalElement) -> HierarchicalElement:
    parent = element.get_parent()
    if parent is None:
        return element
    return get_ancestor(parent)
