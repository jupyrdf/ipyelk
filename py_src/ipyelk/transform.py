# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional, Union

import ipywidgets as W
import traitlets as T

from .diagram import ElkDiagram, ElkLabel, ElkNode, ElkPort
from .diagram.elk_model import ElkGraphElement
from .diagram.elk_text_sizer import ElkTextSizer, size_labels
from .exceptions import ElkDuplicateIDError, ElkRegistryError
from .schema import ElkSchemaValidator
from .trait_types import Schema


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Optional[Hashable]
    target: Hashable
    target_port: Optional[Hashable]
    owner: Hashable
    data: Optional[Dict]

    def __hash__(self):
        return hash((self.source, self.source_port, self.target, self.target_port))


@dataclass(frozen=True)
class Port:
    node: Hashable
    elkport: ElkPort

    def __hash__(self):
        return hash(tuple([hash(self.node), hash(self.elkport.id)]))


NodeMap = Dict[Hashable, ElkNode]
EdgeMap = Dict[Hashable, List[Edge]]
PortMap = Dict[Hashable, Port]


class ElkTransformer(W.Widget):
    """ Transform data into the form required by the ElkDiagram. """

    ELK_ROOT_ID = "root"
    _nodes: Optional[Dict[Hashable, ElkNode]] = None
    source = T.Dict()
    value = Schema(ElkSchemaValidator)
    _version: str = "v1"
    _task: asyncio.Task = None

    # internal map between output Elk Elements and incoming items
    _elk_to_item: Dict[str, Hashable] = None
    _item_to_elk: Dict[Hashable, str] = None

    text_sizer: ElkTextSizer = T.Instance(ElkTextSizer, allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.refresh()

    async def transform(self) -> ElkNode:
        """Generate elk json"""
        top = ElkNode(**self.source)
        # bulk calculate label sizes
        await size_labels(self.text_sizer, collect_labels([top]))
        return top

    @T.default("value")
    def _default_value(self):
        return {"id": self.ELK_ROOT_ID}

    async def _refresh(self):
        root_node = await self.transform()
        value = root_node.to_dict()

        # forces redraw on the frontend by creating to new label
        labels = value.get("labels", [])
        labels.append(ElkLabel(id=str(id(value))).to_dict())

        value["labels"] = labels
        self.value = value

    @T.observe("source")
    def refresh(self, change: T.Bunch = None):
        """Method to update this transform's value by scheduling the
        transformation task on event loop
        """
        self.log.debug("Refreshing elk transformer")
        # remove previous refresh task if still pending
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._refresh())

    def from_id(self, element_id: str) -> Hashable:
        """Use the elk identifiers to find original objects"""
        try:
            return self._elk_to_item[element_id]
        except KeyError as E:
            raise ElkRegistryError(
                f"Element id `{element_id}` not in elk id registry."
            ) from E

    def to_id(self, item: Hashable) -> str:
        """Use original objects to find elk id"""
        try:
            return self._item_to_elk[item]
        except KeyError as E:
            raise ElkRegistryError(f"Item `{item}` not in elk id registry.") from E

    def connect(self, view: ElkDiagram) -> T.link:
        """Connect the output value of this transformer to a diagram"""
        return T.dlink((self, "value"), (view, "value"))

    def register(self, element: Union[str, ElkGraphElement], item: Hashable):
        """Register Elk Element as a way to find the particular item.

        This method is used in the `lookup` method for dereferencing the elk id.

        :param element: ElkGraphElement or elk id to track
        :type element: ElkGraphElement
        :param item: [description]
        :type item: Hashable
        """

        _id = element.id if isinstance(element, ElkGraphElement) else element

        if _id in self._elk_to_item:
            raise ElkDuplicateIDError(f"{_id} already exists in the registry")
        self._elk_to_item[_id] = item
        self._item_to_elk[item] = _id

    def clear_registry(self):
        self._elk_to_item: Dict[str, Hashable] = {}
        self._item_to_elk: Dict[Hashable, str] = {}


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
    elif not isinstance(d1, dict):
        d1 = d1.to_dict()
    if d2 is None:
        d2 = {}
    elif not isinstance(d2, dict):
        d2 = d2.to_dict()

    cl1 = d1.get("cssClasses", "")
    cl2 = d2.get("cssClasses", "")
    cl = " ".join(sorted(set([*cl1.split(), *cl2.split()]))).strip()

    value = {**d2, **d1}  # right most wins if duplicated keys

    # if either had cssClasses, update that
    if cl:
        value["cssClasses"] = cl

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


def collect_labels(
    nodes: List[ElkNode], recurse: bool = True, include_sized: bool = False
) -> List[ElkLabel]:
    """Iterate over the map of ElkNodes and pluck labels from:
        * node
        * node.ports
        * node.edges
    If recuse is True then labels from each child will be included

    :param nodes: [description]
    :type nodes: List[ElkNode]
    :param included_sized: Flag to include labels that have already been sized
    :type included_sized: bool
    :return: [description]
    :rtype: List[ElkLabel]
    """
    labels = []

    def include(label):
        return include_sized or not bool(label.width or label.height)

    for elknode in nodes:
        for label in listed(elknode.labels):
            if include(label):
                add_label(labels, label)
        for elkport in listed(elknode.ports):
            for label in listed(elkport.labels):
                if include(label):
                    add_label(labels, label)
        for elkedge in listed(elknode.edges):
            for label in listed(elkedge.labels):
                if include(label):
                    add_label(labels, label)
        if recurse:
            labels.extend(collect_labels(listed(elknode.children)))
    return labels


def add_label(labels: List[ElkLabel], label: Union[Dict, ElkLabel]):
    if not isinstance(label, ElkLabel):
        label = ElkLabel.from_dict(label)
    labels.append(label)
