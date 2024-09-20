# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from collections import defaultdict
from typing import ClassVar, List, Optional
from uuid import uuid4

from pydantic.v1 import BaseModel, Field


def id_factory():
    return defaultdict(lambda: str(uuid4()))


class Registry(BaseModel):
    """Context Manager to generate and maintain a lookup of objects to identifiers"""

    ids: defaultdict = Field(repr=False, default_factory=id_factory)
    stack: ClassVar[List] = []

    class Config:
        copy_on_model_validation = "none"

    def __enter__(self):
        self.get_contexts().append(self)
        return self

    def __exit__(self, typ, value, traceback):
        self.get_contexts().pop()

    @classmethod
    def get_context(cls, error_if_none=True) -> Optional["Registry"]:
        try:
            return cls.get_contexts()[-1]
        except IndexError:
            if error_if_none:
                raise TypeError("No %s on context stack" % str(cls))
            return None

    @classmethod
    def get_contexts(cls) -> List:
        return cls.stack

    @classmethod
    def get_id(cls, key) -> Optional[str]:
        context = cls.get_context(error_if_none=False)
        if context:
            return context[key]

    def __getitem__(self, key):
        return self.ids[key]

    def __hash__(self):
        return hash(id(self))
