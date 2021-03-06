# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional, Union

import ipywidgets as W
import traitlets as T

from . import elements
from .diagram import ElkDiagram, ElkLabel, ElkNode, ElkPort
from .diagram.elk_model import ElkGraphElement
from .diagram.elk_text_sizer import ElkTextSizer, size_labels
from .exceptions import ElkDuplicateIDError, ElkRegistryError
from .schema import ElkSchemaValidator
from .trait_types import Schema
from .util import listed


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Optional[Hashable]
    target: Hashable
    target_port: Optional[Hashable]
    owner: Hashable
    data: Dict
    mark: Optional[elements.Mark]

    def __hash__(self):
        return hash((self.source, self.source_port, self.target, self.target_port))


@dataclass(frozen=True)
class Port:
    node: Hashable
    elkport: ElkPort
    mark: Optional[elements.Mark]

    def __hash__(self):
        return hash(tuple([hash(self.node), hash(self.elkport.id)]))


# TODO investigating following pattern for various map
# https://github.com/pandas-dev/pandas/issues/33025#issuecomment-699636759
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

    text_sizer: ElkTextSizer = T.Instance(ElkTextSizer, allow_none=True, kw={})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.refresh()

    async def transform(self) -> ElkNode:
        """Generate elk json"""
        top = ElkNode(**self.source)
        return top

    @T.default("value")
    def _default_value(self):
        return {"id": self.ELK_ROOT_ID}

    async def _refresh(self, debug=False):
        text_sizer = self.text_sizer
        if debug:
            self.text_sizer = None

        root_node = await self.transform()
        # bulk calculate label sizes
        await size_labels(self.text_sizer, collect_labels([root_node]))
        value = root_node.to_dict()

        # forces redraw on the frontend by creating to new label
        labels = value.get("labels", [])
        labels.append(ElkLabel(id=str(id(value))).to_dict())

        value["labels"] = labels
        self.value = value
        self.text_sizer = text_sizer

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
        """Use original objects to find elk id

        :param item: item to convert to the elk identifier
        :raises ElkRegistryError: If unable to find item in the registry
        :return: elk identifier
        """
        try:
            return self._item_to_elk[item]
        except KeyError as E:
            raise ElkRegistryError(f"Item `{item}` not in elk id registry.") from E

    def connect(self, view: ElkDiagram) -> T.link:
        """Connect the output elk json value of this transformer to a diagram

        :param view: Elk diagram to link elk json values.
        :return: traitlet link
        """
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
    labels: List[ElkLabel] = []

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
