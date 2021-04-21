# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import abc

from pydantic import BaseModel

from ..exceptions import NotFoundError, NotUniqueError


class AbstractInput(BaseModel, abc.ABC):
    """Base source model for transformers to operate on to generate elkjson"""

    _version: str = "v1"

    @classmethod
    def convert(cls, data):
        matches = [i for i in cls.__subclasses__() if i.check(data)]
        num_matches = len(matches)
        if num_matches == 0:
            raise NotFoundError("Unable to get matching transformer for data")
        elif num_matches > 1:
            raise NotUniqueError("Nonunique transformers found: {num_matches}")
        # only one `AbstractInput` can coerce
        _cls = matches[0]
        return _cls.wrap(data)

    @abc.abstractmethod
    def wrap(self, data) -> "AbstractInput":
        """Subclasses wrap data"""

    @abc.abstractmethod
    def check(self, data) -> bool:
        """Subclasses check if they can wrap input data"""
