# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Removed in 3.0: nothing used the module, and nothing replaces it.

This guard exists only to turn a stale import into an actionable error; it
defines nothing.
"""

from ..exceptions import DeprecatedImportError

raise DeprecatedImportError(
    "ipyelk.pipes.mappings was removed in ipyelk 3.0: nothing in ipyelk used its "
    "Edge and Port dataclasses or its NodeMap, EdgeMap and PortMap aliases, and "
    "nothing replaces them. Build graphs from ipyelk.elements.Node, Edge and Port. "
    "No alias: this error is raised throughout 3.x."
)
