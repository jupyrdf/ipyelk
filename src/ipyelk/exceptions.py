# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import functools
import types
from collections.abc import Callable, Iterable


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


class DeprecatedAPI(Exception):
    """Base for the 3.0 tombstones, so one ``except`` catches every flavour.

    The flavours differ only in the second base class, which decides how the
    interpreter treats them; the message is the point in both cases.
    """


class DeprecatedAPIError(DeprecatedAPI, AttributeError):
    """An *attribute* removed in ipyelk 3.0 was read or assigned.

    Removed names are not aliased or forwarded; they raise this error for the whole
    3.x line, and the message says why the name went away and what replaces it.

    An ``AttributeError`` so the tombstones keep Python's attribute contract:
    ``hasattr`` is False, ``getattr(obj, name, default)`` returns the default, and
    :func:`inspect.getmembers` and ``mock.create_autospec`` keep working.
    """


class DeprecatedImportError(DeprecatedAPI, ImportError):
    """A module-level *name* removed in ipyelk 3.0 was imported.

    Deliberately **not** an ``AttributeError``: ``from module import name`` replaces
    an ``AttributeError`` from a module ``__getattr__`` with a bare
    ``ImportError("cannot import name ...")``, which would throw away the migration
    message on the most common upgrade path. An ``ImportError`` subclass is both the
    right type for a name that cannot be imported and one the interpreter passes
    through untouched.
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


class RegistrationMethod:
    """Descriptor for a callback-registration method that is called, never assigned.

    ``instance.name`` is the bound method and ``Owner.name`` the plain function (what
    Sphinx and :mod:`inspect` see), exactly like an ordinary method; assigning
    ``instance.name = callback`` (the 2.x single-slot form) raises
    :class:`DeprecatedAPIError` with ``message``. Constructor keywords are not
    intercepted (see :class:`RemovedAPI`): the owner checks them in ``__init__``.
    """

    def __init__(self, func: Callable, message: str):
        functools.update_wrapper(self, func)
        self.func = func
        self.message = message

    def __get__(self, instance: object, owner: type | None = None) -> Callable:
        if instance is None:
            return self.func
        return types.MethodType(self.func, instance)

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
