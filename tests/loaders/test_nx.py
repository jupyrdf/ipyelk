# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import networkx as nx

from ipyelk.elements import Edge, Port, index
from ipyelk.loaders import NXLoader


def test_nx_port_ids_prefixed_by_node_id():
    graph = nx.MultiDiGraph()
    graph.add_edge("x", "y", sourcePort="out", targetPort="in")
    mark = NXLoader().load(graph=graph)
    try:
        ports = [el for el in index.iter_elements(mark.value) if isinstance(el, Port)]
        edges = [el for el in index.iter_elements(mark.value) if isinstance(el, Edge)]
        assert len(ports) == 2
        for port in ports:
            parent = port.get_parent()
            assert parent is not None
            assert port.id is not None
            assert port.id.startswith(f"{parent.id}.")
            assert port.get_id() == port.id
        assert len(edges) == 1
        edge = edges[0]
        assert edge.sources == [edge.source.id]
        assert edge.targets == [edge.target.id]
        assert {edge.source.get_parent().id, edge.target.get_parent().id} == {
            "x",
            "y",
        }
        # the loader's ids are the ones the index is keyed by
        mark.persist(rebuild_index=True)
        for port in ports:
            assert mark.index.elements.get(port.id) is port
    finally:
        mark.close()
