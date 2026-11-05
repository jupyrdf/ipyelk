"""Report which graph ``examples/04_Interactive.ipynb`` holds, for its robot test."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import hashlib
import json
import sys
import time

import networkx as nx

from ipyelk.elements import Edge, Port, index
from ipyelk.pipes.util import iter_pipes

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


def _read(reader):
    """A broken reader must not hide the other layers of a failed run."""
    try:
        return reader()
    except Exception as err:
        return {"unavailable": f"{type(err).__name__}: {err}"}


def _mark(mark):
    return {
        "model_id": mark.model_id,
        "gen": mark.gen,
        "edges": sorted(
            el.id for el in index.iter_elements(mark.value) if isinstance(el, Edge)
        ),
    }


def _task(task):
    if task is None:
        return {"unavailable": "no task"}
    done, cancelled = task.done(), task.cancelled()
    return {
        "done": done,
        "cancelled": cancelled,
        "error": (str(task.exception()) if task.exception() is not None else None)
        if done and not cancelled
        else None,
    }


def diagnostic_layers(elk):
    """Read identities only; never refresh, await or change the pipeline."""
    marks = {}

    def reference(mark):
        key = mark.model_id
        if key not in marks:
            marks[key] = _read(lambda: _mark(mark))
        return key

    def pipe_state(pipe):
        return {
            "model_id": pipe.model_id,
            "type": type(pipe).__name__,
            "inlet": _read(lambda: reference(pipe.inlet)),
            "outlet": _read(lambda: reference(pipe.outlet)),
            "requested": pipe._requested,
            "generation": pipe._generation,
            "browser_generation": getattr(
                pipe, "_roundtrip_gen", {"unavailable": "not a browser pipe"}
            ),
            "task": _read(lambda: _task(pipe._task)),
            "status_error": _read(
                lambda: (
                    str(pipe.status.exception)
                    if pipe.status.exception is not None
                    else None
                )
            ),
        }

    result = {
        "captured_at": time.time(),
        "source": _read(lambda: reference(elk.source)),
        "viewer": _read(
            lambda: {
                "model_id": elk.view.model_id,
                "source": reference(elk.view.source),
            }
        ),
        "pipes": _read(
            lambda: [_read(lambda p=p: pipe_state(p)) for p in iter_pipes(elk.pipe)]
        ),
        "marks": marks,
    }
    return result


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

    def snapshot():
        values = [sliders[name].value for name in SLIDERS]
        edges = [
            el for el in index.iter_elements(elk.source.value) if isinstance(el, Edge)
        ]
        return {
            "sliders": "/".join(map(str, values)),
            "requested": requested_fingerprint(*values),
            "held": held_fingerprint(edges),
            "edges": sorted(edge.id for edge in edges),
            "changes": changes["count"],
            "changed_at": changes["at"],
        }

    def check(token, diagnostic=False):
        state = _read(snapshot) if diagnostic else snapshot()
        if diagnostic:
            state["layers"] = diagnostic_layers(elk)
        sys.stdout.write(f"{token} {json.dumps(state)}\n")

    return check
