"""Report which graph ``examples/04_Interactive.ipynb`` holds, for its robot test."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import hashlib
import json
import sys
import time

import networkx as nx

from ipyelk.elements import Edge, Port, index

SLIDERS = ("number_of_nodes", "percent_of_edges", "seed")


def _node_id(end):
    return end.get_parent().id if isinstance(end, Port) else end.id


def _fingerprint(pairs):
    return hashlib.sha256(json.dumps(sorted(pairs)).encode()).hexdigest()[:12]


def requested_fingerprint(number_of_nodes, percent_of_edges, seed):
    """Fingerprint the edges ``make_graph`` builds for these slider values."""
    m = max(1, int(number_of_nodes * 0.01 * percent_of_edges))
    graph = nx.barabasi_albert_graph(n=number_of_nodes, m=m, seed=seed)
    return _fingerprint(sorted(map(str, edge)) for edge in graph.edges)


def held_fingerprint(edges):
    """Fingerprint ``elk.source`` edges by the nodes they join."""
    return _fingerprint(sorted([_node_id(e.source), _node_id(e.target)]) for e in edges)


def watch(box, elk):
    """Return ``check(token)``, which prints ``token`` and one line of JSON."""
    sliders = {
        getattr(w, "description", None): w for w in box.children[0].children[0].children
    }
    changes = {"count": 0, "at": time.time()}

    def on_source(_change):
        changes["count"] += 1
        changes["at"] = time.time()

    elk.observe(on_source, "source")

    def check(token):
        values = [sliders[name].value for name in SLIDERS]
        edges = [
            el for el in index.iter_elements(elk.source.value) if isinstance(el, Edge)
        ]
        state = {
            "sliders": "/".join(map(str, values)),
            "requested": requested_fingerprint(*values),
            "held": held_fingerprint(edges),
            "edges": sorted(edge.id for edge in edges),
            "changes": changes["count"],
            "changed_at": changes["at"],
        }
        sys.stdout.write(f"{token} {json.dumps(state)}\n")

    return check
