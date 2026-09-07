# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..model.model import ElkNode, ElkPort

if TYPE_CHECKING:
    from .. import elements


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Hashable | None
    target: Hashable
    target_port: Hashable | None
    owner: Hashable
    data: dict
    mark: elements.Mark | None

    def __hash__(self):
        return hash((self.source, self.source_port, self.target, self.target_port))


@dataclass(frozen=True)
class Port:
    node: Hashable
    elkport: ElkPort
    mark: elements.Mark | None

    def __hash__(self):
        return hash(tuple([hash(self.node), hash(self.elkport.id)]))


# TODO investigating following pattern for various map
# https://github.com/pandas-dev/pandas/issues/33025#issuecomment-699636759
NodeMap = dict[Hashable, ElkNode]
EdgeMap = dict[Hashable, list[Edge]]
PortMap = dict[Hashable, Port]
