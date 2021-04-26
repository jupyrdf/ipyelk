from typing import Dict, List, Union

from ..model.model import ElkLabel, ElkNode
from ..util import listed


def collect_labels(
    nodes: List[ElkNode], recurse: bool = True, include_sized: bool = False
) -> List[ElkLabel]:
    """Iterate over the map of ElkNodes and pluck labels from:
        * node
        * node.ports
        * node.edges
    If recuse is True then labels from each child will be included

    :param nodes: [description]
    :type nodes: List[ElkNode]
    :param included_sized: Flag to include labels that have already been sized
    :type included_sized: bool
    :return: [description]
    :rtype: List[ElkLabel]
    """
    labels: List[ElkLabel] = []

    def include(label):
        return include_sized or not bool(label.width or label.height)

    for elknode in nodes:
        for label in listed(elknode.labels):
            if include(label):
                add_label(labels, label)
        for elkport in listed(elknode.ports):
            for label in listed(elkport.labels):
                if include(label):
                    add_label(labels, label)
        for elkedge in listed(elknode.edges):
            for label in listed(elkedge.labels):
                if include(label):
                    add_label(labels, label)
        if recurse:
            labels.extend(collect_labels(listed(elknode.children)))
    return labels


def add_label(labels: List[ElkLabel], label: Union[Dict, ElkLabel]):
    if not isinstance(label, ElkLabel):
        label = ElkLabel.from_dict(label)
    labels.append(label)
