# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ._version import __version__
from .app import Elk
from .diagram import ElkDiagram, ElkJS


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@jupyrdf/jupyter-elk"}]


__all__ = ["__version__", "Elk", "ElkDiagram", "ElkJS"]
