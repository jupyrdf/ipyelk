# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from abc import ABC
from typing import Hashable
from uuid import uuid4

from .svg import Def


class Symbol(ABC):
    id: Hashable
    shape: Def
    identifier: str
    width: float
    height: float

    def __init__(self, **kwargs):
        if "id" not in kwargs:
            id = uuid4()
        else:
            id = kwargs["id"]
        self.id = id

    def __hash__(self):
        """Simple hashing function to make it easier to use as a networkx node"""
        return hash(self.id)

    @property
    def data():
        """Returns a valid elk node dictionary"""
        pass
