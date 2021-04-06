# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from collections import defaultdict
from dataclasses import dataclass, field
from typing import ClassVar, List, Optional
from uuid import uuid4


def id_factory():
    return defaultdict(lambda: str(uuid4()))


@dataclass
class Registry:
    """Context Manager to generate and maintain a lookup of objects to identifiers"""

    _ids: defaultdict = field(repr=False, default_factory=id_factory)
    _stack: ClassVar[List] = []

    def __enter__(self):
        self.get_contexts().append(self)
        return self

    def __exit__(self, typ, value, traceback):
        self.get_contexts().pop()

    @classmethod
    def get_context(cls, error_if_none=True) -> Optional:
        try:
            return cls.get_contexts()[-1]
        except IndexError:
            if error_if_none:
                raise TypeError("No %s on context stack" % str(cls))
            return None

    @classmethod
    def get_contexts(cls) -> List:
        return cls._stack

    @classmethod
    def get_id(cls, key):
        context = cls.get_context(error_if_none=False)
        if context:
            return context[key]

    def __getitem__(self, key):
        return self._ids[key]

    def __hash__(self):
        return hash(id(self))
