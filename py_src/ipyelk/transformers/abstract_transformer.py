# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import abc
import asyncio
from typing import Dict, Hashable, Optional, Type

from ..elements import Mark
from ..exceptions import (
    ElkDuplicateIDError,
    ElkRegistryError,
    NotFoundError,
    NotUniqueError,
)
from ..model.model import ElkNode

# from .abstract_input import AbstractInput

# from .schema import ElkSchemaValidator
# from .trait_types import Schema


class AbstractTransformer(abc.ABC):
    """ Transform data into the form required by the ElkDiagram. """

    ELK_ROOT_ID = "root"
    _nodes: Optional[Dict[Hashable, ElkNode]] = None
    _task: asyncio.Task = None

    # internal map between output Elk Elements and incoming items
    _elk_to_item: Dict[str, Hashable] = None
    _item_to_elk: Dict[Hashable, str] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_registry()

    @abc.abstractmethod
    async def transform(self, data) -> ElkNode:
        """Generate elk json"""
        # TODO should run elkschemavalidator?

    @abc.abstractclassmethod
    def check(cls, data) -> bool:
        """Check if this transformer can operate on input datatype"""

    @classmethod
    def get_transformer_cls(cls, data) -> Type["AbstractTransformer"]:
        matches = [t for t in cls.__subclasses__() if t.check(data)]
        # handle if multiple match
        num_matches = len(matches)
        if num_matches == 1:
            return matches[0]
        elif num_matches == 0:
            raise NotFoundError("Unable to get matching transformer for data")
        else:
            raise NotUniqueError("Nonunique transformers found: {num_matches}")

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

    def register(self, mark: Mark):
        """Register Elk Element as a way to find the particular item.

        This method is used in the `lookup` method for dereferencing the elk id.

        :param element: ElkGraphElement or elk id to track
        :type element: ElkGraphElement
        :param item: [description]
        :type item: Hashable
        """

        _id = mark.get_id()

        if _id in self._elk_to_item:
            raise ElkDuplicateIDError(f"{_id} already exists in the registry")
        self._elk_to_item[_id] = mark
        self._item_to_elk[mark] = _id

    def clear_registry(self):
        self._elk_to_item: Dict[str, Hashable] = {}
        self._item_to_elk: Dict[Hashable, str] = {}
