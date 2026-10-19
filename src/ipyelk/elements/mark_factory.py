# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Removed in 3.0: ``Mark`` and ``MarkFactory`` served the networkx transformer
that 2.0 removed, and nothing used them since.

This guard exists only to turn a stale import into an actionable error; it
defines nothing.
"""

from ..exceptions import DeprecatedImportError

raise DeprecatedImportError(
    "ipyelk.elements.mark_factory was removed in ipyelk 3.0: its Mark and "
    "MarkFactory classes served the networkx transformer that ipyelk 2.0 removed "
    "(#90), and nothing used them since. To use one fragment in several places, "
    "copy it with Node.clone(prefix); to load a networkx graph, use ipyelk.from_nx "
    "or ipyelk.loaders.NXLoader. No alias: this error is raised throughout 3.x."
)
