# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Removed in 3.0: the module was renamed to :mod:`ipyelk.tools.control_overlay`.

This guard exists only to turn a stale import into an actionable error; it does
not forward to the renamed module.
"""

from ..exceptions import DeprecatedImportError

raise DeprecatedImportError(
    "ipyelk.tools.contol_overlay (misspelled) was removed in ipyelk 3.0; import "
    "ControlOverlay from ipyelk.tools.control_overlay (or ipyelk.tools). No alias: "
    "this error is raised throughout 3.x."
)
