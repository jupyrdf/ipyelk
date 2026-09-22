# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Deterministic synthetic graphs for ``bench_pipeline.py``.

Two shapes, both seeded and fully id-assigned (so element ids -- and therefore
serialized byte counts -- do not depend on ``uuid4``):

``flat``
    one root owning ``n`` leaf nodes, ``1.5 n`` edges, one or two labels per
    node and a port on ~30% of them.
``nested``
    the same node/edge/label/port budget arranged as a compound hierarchy three
    levels deep (root -> group -> subgroup -> leaf). Every edge is owned by the
    root, as ``Node.add_edge`` produces them, so ``ValidationPipe`` has to
    compute each edge's lowest common ancestor.
"""

from __future__ import annotations

import math
import random
from collections import Counter

from ipyelk.elements import Edge, Label, Node, Port
from ipyelk.elements.elements import PortProperties

EDGES_PER_NODE = 1.5
PORT_FRACTION = 0.3
PORTED_EDGE_FRACTION = 0.5
MIN_GROUP_FOR_SUBGROUPS = 8


def _leaf(i: int, rng: random.Random) -> Node:
    """One leaf node: one or two labels, sometimes an input port."""
    labels = [Label(id=f"n{i}.l0", text=f"node {i}")]
    if i % 2:
        labels.append(Label(id=f"n{i}.l1", text=f"kind {i % 7}"))
    node = Node(id=f"n{i}", labels=labels)
    if rng.random() < PORT_FRACTION:
        node.add_port(
            Port(id=f"n{i}.in", width=5, height=5, properties=PortProperties()),
            key="in",
        )
    return node


def _add_edges(root: Node, leaves: list[Node], rng: random.Random) -> None:
    """Wire ``1.5 n`` root-owned edges between random leaves."""
    n = len(leaves)
    for e in range(int(EDGES_PER_NODE * n)):
        u = rng.randrange(n)
        v = rng.randrange(n)
        if u == v:
            v = (v + 1) % n
        source: Node | Port = leaves[u]
        target: Node | Port = leaves[v]
        if leaves[v].ports and rng.random() < PORTED_EDGE_FRACTION:
            target = leaves[v].ports[0]
        edge: Edge = root.add_edge(source=source, target=target)
        edge.id = f"e{e}"


def flat(n: int, seed: int = 0) -> Node:
    """``n`` leaves directly under the root."""
    rng = random.Random(seed)  # ruff: ignore[suspicious-non-cryptographic-random-usage]
    leaves = [_leaf(i, rng) for i in range(n)]
    root = Node(id="root")
    for leaf in leaves:
        root.add_child(leaf)
    _add_edges(root, leaves, rng)
    return root


def nested(n: int, seed: int = 0) -> Node:
    """``n`` leaves in a compound hierarchy three levels below the root."""
    rng = random.Random(seed)  # ruff: ignore[suspicious-non-cryptographic-random-usage]
    leaves = [_leaf(i, rng) for i in range(n)]
    root = Node(id="root")
    n_groups = max(1, int(math.sqrt(n) / 2))
    groups: list[list[Node]] = [[] for _ in range(n_groups)]
    for i, leaf in enumerate(leaves):
        groups[i % n_groups].append(leaf)

    for gi, members in enumerate(groups):
        group = Node(id=f"g{gi}", labels=[Label(id=f"g{gi}.l0", text=f"group {gi}")])
        root.add_child(group)
        # half the groups get a third level; the rest hold their leaves directly
        n_sub = (
            2 + gi % 2 if len(members) > MIN_GROUP_FOR_SUBGROUPS and gi % 2 == 0 else 0
        )
        if not n_sub:
            for leaf in members:
                group.add_child(leaf)
            continue
        for si in range(n_sub):
            sub = Node(
                id=f"g{gi}.s{si}",
                labels=[Label(id=f"g{gi}.s{si}.l0", text=f"sub {gi}.{si}")],
            )
            group.add_child(sub)
            for leaf in members[si::n_sub]:
                sub.add_child(leaf)
    _add_edges(root, leaves, rng)
    return root


GENERATORS = {"flat": flat, "nested": nested}


def count_elements(root: Node) -> dict[str, int]:
    """Count elements by type, plus the maximum node depth below the root."""
    from ipyelk.elements import index

    counts: Counter[str] = Counter()
    for el in index.iter_elements(root):
        counts[type(el).__name__] += 1

    def depth(node: Node) -> int:
        return 1 + max((depth(c) for c in node.children), default=0)

    out = {k: counts[k] for k in ("Node", "Port", "Edge", "Label") if counts[k]}
    out["total"] = sum(counts.values())
    out["depth"] = depth(root) - 1
    return out
