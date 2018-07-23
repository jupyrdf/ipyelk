#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Dane Freeman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget
from traitlets import Dict, Unicode
from ._version import EXTENSION_SPEC_VERSION

module_name = "elk-widget"


class ELKWidget(DOMWidget):
    """TODO: Add docstring here
    """
    _model_name = Unicode('ELKModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = Unicode('ELKView').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    value = Dict().tag(sync=True)
    layout = Dict().tag(sync=True)
