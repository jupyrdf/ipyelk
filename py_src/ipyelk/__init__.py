# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ._version import __version__
from .diagram import Diagram
from .transformers import AbstractTransformer


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@jupyrdf/jupyter-elk"}]


__all__ = ["__version__", "Diagram", "AbstractTransformer"]
