"""Deterministic two-view tool contracts for the real-browser acceptance suite."""

# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
import json
import os
import re
import subprocess
import sys

import ipywidgets as W
from IPython.display import display

from ipyelk import Diagram
from ipyelk.diagram import Exporter, SprottyViewer
from ipyelk.elements import Label, Node, NodeProperties, NodeShape, Port
from ipyelk.pipes import (
    BrowserTextSizer,
    ElkJS,
    MarkElementWidget,
    Pipeline,
    ValidationPipe,
    VisibilityPipe,
)
from ipyelk.pipes import flows as F
from ipyelk.tools import ControlOverlay, Selection, ToggleCollapsedTool, Viewport


class CountValidation(ValidationPipe):
    calls = 0

    async def run(self):
        self.calls += 1
        return await super().run()


class CountText(BrowserTextSizer):
    requests = 0

    def send(self, content, buffers=None):
        if content.get("action") == "run":
            self.requests += 1
        return super().send(content, buffers)


class CountLayout(ElkJS):
    calls = 0

    async def run(self):
        self.calls += 1
        return await super().run()


def tree():
    """Explicit dimensions make both pointer targets and geometry meaningful."""
    return Node(
        id="tools-root",
        children=[
            Node(
                id="tools-a",
                properties=NodeProperties(
                    cssClasses="tools-model-class",
                    shape=NodeShape(width=160, height=90),
                ),
                labels=[Label(id="tools-label", text="Tool target")],
                ports=[Port(id="tools-port", width=12, height=12)],
            ),
            Node(
                id="tools-b",
                width=100,
                height=60,
                labels=[Label(id="tools-label-b", text="Other target")],
            ),
            Node(
                id="tools-parent",
                children=[Node(id="tools-child", width=60, height=30)],
            ),
        ],
    )


class CountViewport(Viewport):
    def __init__(self, **kwargs):
        self.updates = []
        super().__init__(**kwargs)

    def set_state(self, sync_data):
        self.updates.append(dict(sync_data))
        return super().set_state(sync_data)


class Probe:
    def __init__(self):
        self.validation, self.text, self.elk = (
            CountValidation(),
            CountText(),
            CountLayout(),
        )
        self.hover_changes, self.camera_changes = [], []
        self.selection = Selection(ids=("tools-a",))
        self.diagram = Diagram(
            source=MarkElementWidget(value=tree()),
            pipe=Pipeline(
                pipes=[self.validation, self.text, VisibilityPipe(), self.elk]
            ),
            view=SprottyViewer(selection=self.selection, viewport=CountViewport()),
            layout=W.Layout(height="300px"),
        )
        # Retain the first layout task before any later operation can coalesce it.
        self.initial_task = self.diagram.refresh()
        self.operation = "ready"
        self.task = asyncio.create_task(self.ready())
        self.diagram.add_class("tools-probe")
        # The tool contracts drive the canvas; a floating toolbar can cover labels.
        self.diagram.toolbar.layout.display = "none"
        self.diagram.view.hover.observe(
            lambda c: self.hover_changes.append(c.new), "hovered_id"
        )
        self.diagram.view.viewport.observe(self.camera_changed, "origin")
        display(W.HBox([self.diagram, self.diagram], layout=W.Layout(height="320px")))

    def camera_changed(self, change):
        camera = self.diagram.view.viewport
        self.camera_changes.append({
            "view": camera.view_id,
            "origin": change.new,
            "zoom": camera.zoom,
        })

    async def ready(self):
        assert self.initial_task is not None
        await self.initial_task
        assert self.elk.calls > 0
        assert self.text.requests > 0, "no actual browser text measurement was counted"

    def operation_state(self):
        """Pending, cancelled and failed work must never look successful."""
        done = self.task is not None and self.task.done()
        error = self.diagram.pipe.status.exception
        cancelled = done and self.task.cancelled()
        if done:
            error = "cancelled" if cancelled else self.task.exception() or error
        return {
            "operation": self.operation,
            "done": done,
            "cancelled": cancelled,
            "error": None if error is None else str(error),
        }

    def start(self, operation):
        """Schedule browser-dependent work and immediately return the cell."""
        if operation not in {"relayout", "collapse", "refresh_burst", "headless"}:
            raise ValueError(f"Unknown tool probe operation: {operation}")
        state = self.operation_state()
        if not state["done"] or state["error"] is not None:
            raise RuntimeError(f"Previous operation did not succeed: {state}")
        self.operation = operation
        self.task = asyncio.create_task(getattr(self, operation)())

    def report(self, token):
        view = self.diagram.view
        state = dict(
            selection=list(view.selection.ids),
            hovered=view.hover.hovered_id,
            hover_changes=self.hover_changes,
            camera_changes=self.camera_changes,
            camera_id=view.viewport.view_id,
            camera_updates=view.viewport.updates,
            export_ready=bool(getattr(getattr(self, "exporter", None), "value", None)),
            elk=self.elk.calls,
            validation=self.validation.calls,
            text=self.text.requests,
            source=self.diagram.source.value.model_dump(mode="json"),
        )
        state.update(self.operation_state())
        sys.stdout.write(f"{token} {json.dumps(state)}\n")

    def reset_events(self):
        self.hover_changes.clear()
        self.camera_changes.clear()
        self.diagram.view.viewport.updates.clear()

    def overlay(self):
        self.diagram.view.control_overlay = ControlOverlay(
            children=[W.Button(description="tools-overlay")]
        )

    async def refresh_burst(self):
        before = self.elk.calls
        self.diagram.source.record(F.Layout)
        tasks = [self.diagram.refresh() for _ in range(10)]
        assert len({id(task) for task in tasks}) == 1
        await tasks[0]
        assert self.elk.calls - before == 1, (before, self.elk.calls)

    async def collapse(self):
        before = self.text.requests, self.validation.calls
        self.selection.ids = ("tools-parent",)
        await self.diagram.get_tool(ToggleCollapsedTool).trigger()
        await self.diagram.refresh()
        assert self.diagram.source.value.children[2].children[0].properties.hidden
        assert (self.text.requests, self.validation.calls) == before

    async def relayout(self):
        self.diagram.source.record(F.Layout)
        await self.diagram.refresh()

    def export(self):
        self.exporter = Exporter(viewer=self.diagram.view, strip_ids=False)
        display(self.exporter)

    def assert_export(self):
        classes = re.findall(r'class="([^"]*)"', self.exporter.value or "")
        assert any("tools-painted" in value.split() for value in classes)
        assert "tools-painted" not in json.dumps(
            self.diagram.source.value.model_dump(mode="json")
        )

    async def headless(self):
        """A separate process has no kernel comm manager and no browser client."""
        code = """
import asyncio
from tool_probe import tree, CountText, CountLayout
from ipyelk import Diagram
from ipyelk.pipes import MarkElementWidget, Pipeline, ValidationPipe, VisibilityPipe
async def main():
    text, elk = CountText(timeout=0.1), CountLayout(timeout=0.1)
    d = Diagram(source=MarkElementWidget(value=tree()),
        pipe=Pipeline(pipes=[ValidationPipe(), text, VisibilityPipe(), elk]))
    try:
        await asyncio.wait_for(d.refresh(), 5)
        assert d.view.source.value is not None
        assert elk.calls == 1
        assert text.requests == 0
    finally:
        d.close()
asyncio.run(main())
"""
        env = dict(os.environ, IPYELK_NO_BROWSER="1")
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stdout + result.stderr
