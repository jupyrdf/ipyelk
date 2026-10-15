# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import math
import numbers
from collections import namedtuple
from decimal import Decimal
from typing import Annotated, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    PlainSerializer,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    WrapSerializer,
)
from typing_extensions import TypeAlias

Sentinel = namedtuple("Sentinel", [])
EMPTY_SENTINEL = Sentinel

ModelT = TypeVar("ModelT", bound=BaseModel)

#: The validation context of ``from_wire``.
WIRE_CONTEXT = {"ipyelk": "wire"}


def from_wire(model: type[ModelT], data: dict) -> ModelT:
    """Validate ``data`` as ``model``, and ignore the keys that the models do not have.

    The elements, their properties and their shapes reject an unknown key, which is
    usually a typo. ELK JSON from the frontend, from ELK or from a file can have keys that
    the models do not have, for example ``junctionPoints`` on an edge. So can the
    attributes of a ``networkx`` graph, which the ``networkx`` loader passes through.
    """
    return model.model_validate(data, extra="ignore", context=WIRE_CONTEXT)


def elk_option_value(value: object) -> object:
    """Write a ``bool`` or a number as the string ELK reads, keep anything else.

    A ``bool`` (also ``numpy.bool_``) becomes ``"true"`` or ``"false"``. An integer
    (any ``numbers.Integral``, for example ``numpy.int64``) becomes ``str(int(v))``.
    Any other real number (``float``, ``numpy.float64``, ``Fraction``, ``Decimal``)
    becomes a plain ``float`` first. A whole-number ``float`` below ``2**53`` in
    magnitude loses its fraction (``2.0`` -> ``"2"``), because ELK's integer parser
    rejects ``"2.0"`` and then ignores the option. A larger ``float`` keeps the form
    ``repr`` gives it (``2.0**53`` -> ``"9007199254740992.0"``, ``1e16`` ->
    ``"1e+16"``): its digits are not exact, and ELK's integer options cannot hold it.

    :raises ValueError: for ``nan`` or an infinity
    """
    # before ``Integral``: ``bool`` is an ``int``. ``numpy.bool_`` is not a number
    # type, so it is found by name, without importing ``numpy`` (optional)
    if isinstance(value, bool) or (
        type(value).__module__ == "numpy" and type(value).__name__ in {"bool", "bool_"}
    ):
        return "true" if value else "false"
    if isinstance(value, numbers.Integral):
        return str(int(value))
    if isinstance(value, (numbers.Real, Decimal)):  # ``Decimal`` is not a ``Real``
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"ELK cannot read the layout option value {value!r}")
        if number.is_integer() and abs(number) < 2**53:  # every such integer is exact
            return str(int(number))
        # ``float(...)``: a subclass's ``repr`` can add a wrapper, for example ``numpy`` 2
        # gives ``"np.float64(12.5)"``, which ELK ignores
        return repr(number)
    return value


def serialize_layout_options(
    options: dict, handler: SerializerFunctionWrapHandler, info: SerializationInfo
):
    """Serialize a ``LayoutOptions`` dictionary, but not a ``None`` value.

    A ``None`` value can only be set in place, because validation rejects it. With
    ``exclude_none=True`` the key is dropped, so ELK uses the option's default.

    :raises ValueError: for a ``None`` value without ``exclude_none=True``, because
        the ELK importer cannot read it
    """
    data = handler(options)
    if info.exclude_none:
        return {key: value for key, value in data.items() if value is not None}
    for key, value in data.items():
        if value is None:
            raise ValueError(
                f"layoutOptions[{key!r}] is None: ELK cannot read it. "
                "Delete the key to unset the option."
            )
    return data


#: ELK layout options: option ids to values, both strings. Validation (on pydantic
#: elements) writes ``bool`` and number values as strings and rejects other types.
#: Serialization writes them as strings too, because a value set in place on the
#: dictionary skips validation. It drops a ``None`` value with ``exclude_none=True``
#: and raises ``ValueError`` for one without.
LayoutOptions: TypeAlias = Annotated[
    dict[
        str,
        Annotated[
            str,
            BeforeValidator(elk_option_value),
            PlainSerializer(elk_option_value, return_type=object),
        ],
    ],
    WrapSerializer(serialize_layout_options),
]


def serialize_value(data: dict, key: str, value, info: SerializationInfo) -> None:
    """Add a derived ELK value while respecting the caller's field selection."""
    if info.include is not None and key not in info.include:
        return
    if info.exclude is not None:
        if isinstance(info.exclude, set) and key in info.exclude:
            return
        if isinstance(info.exclude, dict):
            excluded = info.exclude.get(key)
            if excluded is True or excluded is Ellipsis:
                return
    if value is None and info.exclude_none:
        data.pop(key, None)
    else:
        data[key] = value


class CounterContextManager:
    counter = 0
    active: bool = False

    def __enter__(self):
        if self.counter == 0:
            self.active = True
        self.counter += 1
        return self

    def __exit__(self, *exc):
        if self.counter == 1:
            self.active = False
        if self.counter >= 1:
            self.counter -= 1
