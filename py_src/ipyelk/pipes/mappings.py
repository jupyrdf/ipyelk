# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional

from .. import elements  # import Mark, Node, BaseElement
from ..model.model import ElkNode, ElkPort


@dataclass(frozen=True)
class Edge:
    source: Hashable
    source_port: Optional[Hashable]
    target: Hashable
    target_port: Optional[Hashable]
    owner: Hashable
    data: Dict
    mark: Optional[elements.Mark]

    def __hash__(self):
        return hash((self.source, self.source_port, self.target, self.target_port))


@dataclass(frozen=True)
class Port:
    node: Hashable
    elkport: ElkPort
    mark: Optional[elements.Mark]

    def __hash__(self):
        return hash(tuple([hash(self.node), hash(self.elkport.id)]))


# TODO investigating following pattern for various map
# https://github.com/pandas-dev/pandas/issues/33025#issuecomment-699636759
NodeMap = Dict[Hashable, ElkNode]
EdgeMap = Dict[Hashable, List[Edge]]
PortMap = Dict[Hashable, Port]
