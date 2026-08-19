# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from ipyelk.tools import Tool


def test_on_run_handlers_are_per_instance():
    tool_a = Tool()
    tool_b = Tool()
    assert tool_a._on_run_handlers is not tool_b._on_run_handlers


def test_on_run_callback_does_not_leak_across_instances():
    tool_a = Tool()
    tool_b = Tool()
    calls = []
    tool_a.on_run(calls.append)

    # Fire tool_b's dispatcher; tool_a's callback must NOT run.
    tool_b._on_run_handlers(tool_b)
    assert calls == []

    # Firing tool_a's dispatcher DOES run its callback.
    tool_a._on_run_handlers(tool_a)
    assert calls == [tool_a]
