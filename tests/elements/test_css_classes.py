# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``add_class`` / ``remove_class`` keep the caller's class order (#262).

Before 3.0.1 both methods rebuilt ``cssClasses`` from a ``set``, so the
order followed the process hash seed: the same model serialized to
different bytes in different kernels, and ``VisibilityPipe.clear_slack``
(which calls ``remove_class`` on every port and edge on every refresh)
could reorder a class list between two consecutive passes.
"""

import json
import subprocess
import sys

import pytest

from ipyelk.elements import Node, Port
from ipyelk.elements.index import VisIndex


def test_add_class_appends_in_call_order_without_duplicates() -> None:
    node = Node().add_class("b", "a").add_class("c", "a")
    assert node.properties.cssClasses == "b a c"


def test_remove_class_keeps_the_order_of_the_survivors() -> None:
    node = Node().add_class("c", "b", "a").remove_class("b", "missing")
    assert node.properties.cssClasses == "c a"


def test_remove_class_is_a_no_op_when_nothing_is_removed() -> None:
    port = Port()
    port.properties.cssClasses = "sysml-adornment sysml-port sysml-port-in"
    port.remove_class("slack-port")
    assert port.properties.cssClasses == "sysml-adornment sysml-port sysml-port-in"


def test_clear_slack_leaves_a_port_without_slack_untouched() -> None:
    port = Port()
    port.properties.cssClasses = "sysml-adornment sysml-port sysml-port-in"
    node = Node(ports=[port])
    VisIndex().clear_slack(node)
    assert port.properties.cssClasses == "sysml-adornment sysml-port sysml-port-in"


_SCRIPT = """
import json
from ipyelk.elements import Port
port = Port()
port.properties.cssClasses = "sysml-adornment sysml-port sysml-port-in"
for _ in range(3):
    port.remove_class("slack-port")
    port.add_class("x").remove_class("x")
print(json.dumps(port.properties.cssClasses))
"""


@pytest.mark.parametrize("seed", ["0", "12", "154", "1075"])
def test_class_order_is_independent_of_the_hash_seed(seed: str) -> None:
    # 1075 is the seed that reordered "sysml-port sysml-port-in" on stock 3.0.0
    out = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        check=True,
        capture_output=True,
        text=True,
        env={"PYTHONHASHSEED": seed, "PATH": "", "PYTHONPATH": ":".join(sys.path)},
    )
    assert json.loads(out.stdout) == "sysml-adornment sysml-port sysml-port-in"
