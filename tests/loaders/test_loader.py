# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import networkx as nx
import pytest
import traitlets as T

from ipyelk.elements import Node
from ipyelk.loaders import ElementLoader, ElkJSONLoader, NXLoader
from ipyelk.loaders.loader import Loader

OPTS = (
    "default_node_opts",
    "default_root_opts",
    "default_label_opts",
    "default_port_opts",
    "default_edge_opts",
)


def test_clear_defaults_sets_none_and_notifies_observers():
    loader = Loader()
    seen = []
    loader.observe(lambda change: seen.append(change.name), names=list(OPTS))

    assert loader.clear_defaults() is loader

    assert loader.default_node_opts is None
    assert loader.default_root_opts is None
    assert loader.default_label_opts is None
    assert loader.default_port_opts is None
    assert loader.default_edge_opts is None
    assert sorted(seen) == sorted(OPTS)
    assert loader.get_default_opts(Node()) == {}


def test_cleared_defaults_still_validate():
    loader = Loader().clear_defaults()
    with pytest.raises(T.TraitError):
        loader.set_trait("default_node_opts", "not a dict")


def test_loaders_preserve_keyword_inputs():
    marks = [
        ElementLoader().load(root=Node(id="root")),
        ElkJSONLoader().load(data={"id": "root"}),
        NXLoader().load(graph=nx.MultiDiGraph([(0, 1)])),
    ]
    try:
        assert all(isinstance(mark.value, Node) for mark in marks)
    finally:
        for mark in marks:
            mark.close()


def test_cleared_loader_leaves_layout_options_empty():
    root = Node(children=[Node()])
    ElementLoader().clear_defaults().load(root)
    assert root.layoutOptions == {}
    assert root.children[0].layoutOptions == {}
