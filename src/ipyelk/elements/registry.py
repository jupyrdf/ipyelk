# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import warnings
from typing import ClassVar
from uuid import uuid4
from weakref import WeakKeyDictionary

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return str(uuid4())


#: the warning that constructing a ``Registry`` emits through 3.x
REGISTRY_DEPRECATED = (
    "ipyelk.elements.Registry is deprecated and will be removed in ipyelk 4.0: a "
    "Document (ipyelk.elements.Document) owns the ids of an element tree, without "
    "a context manager. Document(root) gives each element without an id the id "
    "that it serializes with, and document.resolve(id) finds the element; to reuse "
    "a fragment, copy it with Node.clone(prefix). Registry keeps working through 3.x."
)


class Registry(BaseModel):
    """Deprecated: a :class:`~ipyelk.elements.Document` owns the ids. Removed in 4.0.

    Context Manager to generate and maintain a lookup of objects to identifiers.
    The lookup holds its objects weakly: an element that nothing else uses is
    collected, and its entry goes with it. Constructing one emits a
    ``DeprecationWarning``; ipyelk itself never enters one.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ids: WeakKeyDictionary = Field(repr=False, default_factory=WeakKeyDictionary)
    stack: ClassVar[list] = []

    def __init__(self, **data: object) -> None:
        warnings.warn(REGISTRY_DEPRECATED, DeprecationWarning, stacklevel=2)
        super().__init__(**data)

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
        """The id of ``key``, minted on first use."""
        el_id = self.ids.get(key)
        if el_id is None:
            el_id = self.ids[key] = new_id()
        return el_id

    def __hash__(self):
        return hash(id(self))
