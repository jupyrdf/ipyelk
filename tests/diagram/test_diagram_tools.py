# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Diagram`` wires its refresh as an ``on_done`` listener without owning the slot."""

from unittest import mock

from ipyelk.diagram import Diagram
from ipyelk.tools import ToggleCollapsedTool, Tool


class _Custom(Tool):
    async def run(self):
        pass


def test_diagram_registers_refresh_alongside_user_listeners():
    diagram = Diagram()
    toggle = diagram.get_tool(ToggleCollapsedTool)
    assert toggle._on_done_handlers.callbacks.count(diagram.refresh) == 1

    seen = []
    toggle.on_done(seen.append)  # a user listener does not displace the refresh
    with mock.patch.object(diagram.pipe, "schedule_run", return_value=None) as run:
        toggle._on_done_handlers(toggle)
    assert seen == [toggle]
    assert run.call_count == 1


def test_replacing_tools_unregisters_refresh_from_the_old_ones():
    diagram = Diagram()
    old = diagram.get_tool(ToggleCollapsedTool)
    new = _Custom()
    diagram.tools = (new,)
    assert diagram.refresh not in old._on_done_handlers.callbacks
    assert old.tee is None
    assert diagram.refresh in new._on_done_handlers.callbacks
    assert new.tee is diagram.pipe
