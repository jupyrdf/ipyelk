# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid4())


def id_factory():
    return defaultdict(new_id)


class Registry(BaseModel):
    """Context Manager to generate and maintain a lookup of objects to identifiers"""

    ids: defaultdict[Any, Annotated[str, Field(default_factory=new_id)]] = Field(
        repr=False, default_factory=id_factory
    )
    stack: ClassVar[list] = []

    def __enter__(self):
        self.get_contexts().append(self)
        return self

    def __exit__(self, typ, value, traceback):
        self.get_contexts().pop()

    @classmethod
    def get_context(cls, error_if_none=True) -> Registry | None:
        try:
            return cls.get_contexts()[-1]
        except IndexError:
            if error_if_none:
                raise TypeError("No %s on context stack" % str(cls))
            return None

    @classmethod
    def get_contexts(cls) -> list:
        return cls.stack

    @classmethod
    def get_id(cls, key, default: str | None = None) -> str | None:
        """The active context's id for ``key``; ``None`` with no context.

        ``default`` seeds the context when it has not seen ``key`` yet, so an id
        already used elsewhere (an element's wire id) becomes the registered one.
        """
        context = cls.get_context(error_if_none=False)
        if not context:
            return None
        if default is not None and key not in context.ids:
            context.ids[key] = default
        return context[key]

    def __getitem__(self, key):
        return self.ids[key]

    def __hash__(self):
        return hash(id(self))
