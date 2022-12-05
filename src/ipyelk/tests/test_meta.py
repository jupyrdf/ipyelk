# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import ipyelk

try:
    from importlib.metadata import version
except Exception:
    from importlib_metadata import version


def test_meta():
    assert hasattr(ipyelk, "__version__")
    assert ipyelk.__version__ == version("ipyelk")
