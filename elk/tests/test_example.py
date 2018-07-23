#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import pytest

from ..example import ELKWidget


def test_example_creation_blank():
    w = ELKWidget()
    assert w.value == 'Hello World'
