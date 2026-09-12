# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from collections.abc import Iterable


class ElkDuplicateIDError(Exception):
    """Elk Ids must be unique"""


class ElkRegistryError(Exception):
    """Transformer mark registry missing key"""


class NotFoundError(Exception):
    pass


class NotUniqueError(Exception):
    pass


class BrokenPipe(Exception):
    pass


class DeprecatedAPIError(RuntimeError):
    """A name removed in ipyelk 3.0 was used.

    Removed names are not aliased or forwarded; they raise this error for the whole
    3.x line, and the message says why the name went away and what replaces it.
    """


class RemovedAPI:
    """Tombstone descriptor for a removed class attribute.

    Reading or assigning the attribute on an instance raises
    :class:`DeprecatedAPIError` with ``message``; class-level access
    (``Owner.name``, what Sphinx and :mod:`inspect` do) returns the descriptor itself
    and never raises. Constructor keywords are not intercepted by the descriptor
    protocol (``traitlets`` only warns about unknown keywords): a class that wants
    ``Owner(name=...)`` to raise calls :func:`check_removed` in ``__init__``.
    """

    def __init__(self, message: str):
        self.message = message
        self.__doc__ = (
            f"Removed in 3.0; raises DeprecatedAPIError throughout 3.x. {message}"
        )

    def __get__(self, instance: object, owner: type | None = None) -> RemovedAPI:
        if instance is None:
            return self
        raise DeprecatedAPIError(self.message)

    def __set__(self, instance: object, value: object) -> None:
        raise DeprecatedAPIError(self.message)


def check_removed(cls: type, names: Iterable[str]) -> None:
    """Raise :class:`DeprecatedAPIError` if any of ``names`` is a :class:`RemovedAPI`
    attribute of ``cls`` -- the constructor-keyword half of the tombstone contract.
    """
    for name in names:
        removed = getattr(cls, name, None)
        if isinstance(removed, RemovedAPI):
            raise DeprecatedAPIError(removed.message)
