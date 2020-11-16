# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
from typing import Dict, Hashable, Optional, Union

import ipywidgets as W
import traitlets as T

from .diagram import ElkDiagram, ElkLabel, ElkNode
from .diagram.elk_model import ElkGraphElement
from .schema import ElkSchemaValidator
from .trait_types import Schema


class ElkTransformer(W.Widget):
    """ Transform data into the form required by the ElkDiagram. """

    _nodes: Optional[Dict[Hashable, ElkNode]] = None
    source = T.Dict()
    value = Schema(ElkSchemaValidator)
    _version: str = "v1"
    _task: asyncio.Task = None

    # internal map between output Elk Elements and incoming items
    _elk_to_item: Dict[str, Hashable] = None
    _item_to_elk: Dict[Hashable, str] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.refresh()

    async def transform(self) -> ElkNode:
        """Generate elk json"""
        return ElkNode(**self.source)

    @T.default("value")
    def _default_value(self):
        return {"id": "root"}

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
        return element_id

    def to_id(self, item: Hashable) -> str:
        """Use original objects to find elk id"""
        return item

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


class ElkDuplicateIDError(Exception):
    """Elk Ids must be unique"""

    pass
