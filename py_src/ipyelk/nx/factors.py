# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


from typing import Generator, Iterable, List, Tuple

import networkx as nx

from .nx import get_ports


def get_factors(G: nx.MultiDiGraph) -> Generator[Tuple[List, List], None, None]:
    fg = nx.DiGraph()
    variables = set()
    for source, target, edge_data in G.edges(data=True):

        source_port, target_port = get_ports(edge_data)

        source_var = (source, source_port)
        target_var = (target, target_port)

        variables.add(source_var)
        variables.add(target_var)

        fg.add_node(source)
        fg.add_node(source_var)
        fg.add_node(target)
        fg.add_node(target_var)

        fg.add_edge(source, source_var)
        fg.add_edge(target, target_var)
        fg.add_edge(source_var, target_var)

    return split(fg.subgraph(variables))


def split(variable_graph: nx.DiGraph) -> Generator[Tuple[List, List], None, None]:
    for factor in nx.weakly_connected_components(variable_graph):
        sources = []
        targets = []
        for var in factor:
            if variable_graph.in_degree(var) == 0:
                sources.append(var)
            else:
                targets.append(var)

        assert len(sources) >= 1, "Expected at least one source"
        assert len(targets) >= 1, "Expected at least one target"
        yield sources, targets


def invert(mask):
    return map(lambda m: not m, mask)


def keep(items: Iterable[object], mask: Iterable[bool]) -> Iterable[object]:
    """Filter the items iterable based on the given mask

    :param items: Original iterable of objects
    :type items: Iterable[object]
    :param mask: Mask iterable to use as a filter
    :type mask: Iterable[Bool]
    :return: [description]
    :rtype: Iterable[object]
    :yield: Iterable of objects that pass the mask
    :rtype: Iterable[object]
    """
    for item, test in zip(items, mask):
        if test:
            yield item
