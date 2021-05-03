# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ._version import __version__
from .diagram import Diagram, Viewer
from .pipes import Pipe, Pipeline


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@jupyrdf/jupyter-elk"}]


def from_elkjson(data, **kwargs):
    from .json import ElkJSONLoader

    diagram = Diagram(source=ElkJSONLoader().load(data), **kwargs)
    return diagram


def from_nx(graph, hierarchy=None, **kwargs):
    from .nx import NXLoader

    diagram = Diagram(
        source=NXLoader().load(graph=graph, hierarchy=hierarchy), **kwargs
    )
    return diagram


__all__ = ["__version__", "Diagram", "Viewer", "Pipe", "Pipeline"]
