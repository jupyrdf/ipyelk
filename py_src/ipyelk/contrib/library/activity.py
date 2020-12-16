# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ...diagram.defs import shapes
from ...diagram.defs.connectors import Containment, Rhomb, StraightArrow

# from ...diagram.defs.svg import Circle, Def, Path, Point


def ActivityDiagram():
    defs = {
        "decision": shapes.Diamond(r=12),
        "merge": shapes.Diamond(r=12),
        "final_state": shapes.DoubleCircle(r=6),
        "start_state": shapes.SingleCircle(r=6),
        "exit_state": shapes.XCircle(r=6),
    }

    style = {
        " defs g.final_state > circle:nth-child(2)": {
            "fill": "var(--jp-elk-node-stroke)"
        },
    }

    # def add_activity(kwargs):Hashable:
    #     pass

    # def link_activity(a1, a2):

    #     return a1, a2, source_port, target_port

    # a1 = activity("welrkjosd")

    # g.add_node(a1)
    # g.add_edge(*link_activity(a1, a2))

    return defs, style


def BlockDiagram():

    defs = {
        "composition": Rhomb(r=4),
        "aggregation": Rhomb(r=4),
        "containment": Containment(r=4),
        "directed_association": StraightArrow(r=4),
        "inheritance": StraightArrow(r=4, closed=True),
    }

    style = {
        " .arrow.inheritance": {
            "fill": "none",
        },
        " .arrow.containment": {
            "fill": "none",
        },
        " .arrow.aggregation": {
            "fill": "none",
        },
        " .arrow.directed_association": {
            "fill": "none",
        },
    }
    return defs, style
