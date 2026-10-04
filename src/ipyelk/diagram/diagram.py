# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import weakref
from typing import Iterator, Type

import ipywidgets as W
import traitlets as T

from ..elements import SymbolSpec, symbol_serialization
from ..exceptions import NotFoundError, NotUniqueError
from ..pipes import MarkElementWidget, Pipe
from ..pipes import flows as F
from ..styled_widget import StyledWidget
from ..tools import PipelineProgressBar, ToggleCollapsedTool, Tool, Toolbar
from .sprotty_viewer import SprottyViewer
from .viewer import Viewer


def _iter_pipes(pipe: Pipe) -> Iterator[Pipe]:
    """Yield ``pipe`` and every pipe nested in it, breadth first."""
    pending = [pipe]
    while pending:
        sub = pending.pop(0)
        yield sub
        pending.extend(getattr(sub, "pipes", ()))


class Diagram(StyledWidget):
    """An Elk diagramming widget to help coordinate the
    :py:class:`~ipyelk.diagram.viewer.Viewer` and
    :py:class:`~ipyelk.pipes.Pipe`

    Attributes
    ----------
    source: :py:class:`~ipyelk.pipes.MarkElementWidget`
        input source to the diagram's processing pipe
    pipe: :py:class:`~ipyelk.pipes.Pipe`
        processing pipe (that may contain sub-pipes). Pipes perform various
        tasks like adding x/y and width/height layouts or calculating text label sizes.
        The diagram owns its pipe and every pipe nested in it. A new pipe is
        refused if any pipe in it is closed, owned by another open diagram, or
        part of the current pipe. Replacing the pipe closes the old pipe, its
        sub-pipes and the widgets they created (such as status views), but
        never ``source`` or an inlet/outlet passed in.
    view: :py:class:`~ipyelk.diagram.viewer.Viewer`
        output view that will render the pipe outlet
    tools: tuple :py:class:`~ipyelk.tools.Tool`
        list of tools that a user of the diagram might use to manipulate the
        state of the diagram.
    symbols: :py:class:`~ipyelk.elements.SymbolSpec`
        additional shape definitions that can be used in rendering the diagram.
        For example unique arrow head shapes or custom node shapes.

    """

    source = T.Instance(MarkElementWidget, kw={}, help="Syncs Elk JSON Elements")

    pipe = T.Instance(Pipe).tag(sync=True, **W.widget_serialization)
    view = T.Instance(Viewer).tag(sync=True, **W.widget_serialization)
    tools = W.trait_types.TypedTuple(T.Instance(Tool)).tag(
        sync=True, **W.widget_serialization
    )
    toolbar = T.Instance(Toolbar, kw={})
    symbols = T.Instance(SymbolSpec, kw={}).tag(sync=True, **symbol_serialization)
    #: the runner ``refresh`` last registered ``_update_view`` on
    _refresh_task: asyncio.Future | None = None

    def __init__(self, *args, **kwargs):
        #: links ``_wire_pipe`` made to the current pipe
        self._pipe_links: list[T.directional_link] = []
        super().__init__(*args, **kwargs)
        self.add_class("jp-ElkApp")
        self._update_children()
        self._update_tools()

    @T.default("layout")
    def _default_layout(self):
        return {"height": "100%"}

    @T.default("view")
    def _default_view(self):
        view = SprottyViewer(symbols=self.symbols)
        T.link((self, "symbols"), (view, "symbols"))
        return view

    @T.default("pipe")
    def _default_Pipe(self):
        from .flow import DefaultFlow

        pipe = DefaultFlow()
        self._wire_pipe(pipe)
        return pipe

    def _progress_bars(self) -> list[PipelineProgressBar]:
        return [tool for tool in self.tools if isinstance(tool, PipelineProgressBar)]

    def _wire_pipe(self, pipe: Pipe) -> None:
        """Link ``style`` to every text sizer in the pipe and report its progress."""
        from .flow import BrowserTextSizer

        owner = weakref.ref(self)
        for sub in _iter_pipes(pipe):
            sub._diagram = owner
            if isinstance(sub, BrowserTextSizer):
                self._pipe_links.append(W.dlink((self, "style"), (sub, "style")))
        bars = self._progress_bars()
        if pipe.on_progress is None and bars:
            pipe.on_progress = bars[0].update

    @T.validate("pipe")
    def _validate_pipe(self, proposal: T.Bunch) -> Pipe:
        pipe = proposal["value"]
        current = self._trait_values.get("pipe")
        for sub in _iter_pipes(pipe):
            name = type(sub).__name__
            if sub.comm is None:
                msg = f"{name} is closed; assign a new pipe"
                raise T.TraitError(msg)
            owner = sub._diagram() if sub._diagram else None
            if owner is None or owner.comm is None:
                continue
            if owner is not self:
                msg = f"{name} belongs to another diagram; assign a new pipe"
                raise T.TraitError(msg)
            if pipe is not current:
                msg = (
                    f"{name} is part of the current pipe, which is closed when "
                    "replaced; build a new one"
                )
                raise T.TraitError(msg)
        return pipe

    def _release_pipe(self, pipe: Pipe) -> None:
        """Cancel ``pipe`` and drop the diagram's claim on it and links to it."""
        pipe.cancel()
        for sub in _iter_pipes(pipe):
            sub._diagram = None
        links, self._pipe_links = self._pipe_links, []
        for link in links:
            link.unlink()
        self._refresh_task = None
        for bar in self._progress_bars():
            if pipe.on_progress == bar.update:
                pipe.set_trait("on_progress", None)

    def _unwire_pipe(self, old: Pipe, new: Pipe) -> None:
        """Drop every reference the diagram and its tools hold to ``old``."""
        self._release_pipe(old)
        for bar in self._progress_bars():
            if bar.pipe is old:
                bar.pipe = new
        for tool in self.tools:
            tool.tee = new

    def close(self):
        """Close the diagram and release its pipe, which another diagram may take."""
        pipe = self._trait_values.get("pipe")
        if pipe is not None and pipe._diagram and pipe._diagram() is self:
            self._release_pipe(pipe)
        super().close()

    @T.observe("view")
    def _update_children(self, change: T.Bunch | None = None):
        """Handle if the viewer instance changes by reobserving handler
        functions

        :param change: viewer change event
        """
        # TODO should the `viewer` instance be allowed to change?
        self._update_view_sources()
        self.children = [self.view, self.toolbar]

    def _update_view_sources(self):
        self.source.record(F.New)
        self.pipe.inlet = self.source
        self.view.source = self.pipe.outlet

    @T.observe("pipe", "source", "style")
    def _change_pipe(self, change):
        """Rewire and refresh. A new pipe or source cancels the in-flight run,
        whose answer would land in an index nobody views, and a replaced pipe
        is closed; a style change only requests a new run.
        """
        old = change.old if change.name == "pipe" else None
        if isinstance(old, Pipe):
            self._unwire_pipe(old, change.new)
        if change.name == "pipe":
            self._wire_pipe(change.new)
        elif change.name == "source":
            self.pipe.cancel()
        self._update_view_sources()
        if isinstance(old, Pipe):
            old.close()
        self.refresh()

    @T.default("tools")
    def _default_tools(self) -> list[Tool]:
        return [
            self.view.selection,
            self.view.painter,  # state-only, no UI; bound so elements() can resolve
            self.view.fit_tool,
            self.view.center_tool,
            ToggleCollapsedTool(selection=self.view.selection),
            PipelineProgressBar(),
        ]

    @T.observe("tools")
    def _update_tools(self, change: T.Bunch | None = None):
        if change and isinstance(change.old, tuple):
            for tool in change.old or []:
                tool.tee = None
                tool.on_done(self.refresh, remove=True)

        for tool in self.tools:
            tool.tee = self.pipe
            tool.on_done(self.refresh)

    @T.default("toolbar")
    def _default_toolbar(self):
        toolbar = Toolbar(tools=self.tools)
        T.link((self, "tools"), (toolbar, "tools"))
        return toolbar

    def get_tool(self, tool_type: Type[Tool]) -> Tool:
        """Get the tool that matches the given Tool type.

        :param tool_type: get specific tool instance based on matched type.
        """
        matches = [tool for tool in self.tools if type(tool) is tool_type]
        num_matches = len(matches)
        if num_matches > 1:
            raise NotUniqueError(f"Found too many tools with type {tool_type}")
        if num_matches == 0:
            raise NotFoundError(f"No tool matching type {tool_type}")

        return matches[0]

    def register_tool(self, tool: Tool) -> Diagram:
        """Add a new tool to the diagram.

        :param tool: new tool instance to add to the diagram.
        :type tool: Tool
        :return: current Diagram instance
        """
        # TODO inject dependencies smarter...
        traits = tool.trait_names()
        if "diagram" in traits:
            tool.diagram = self
        if "selection" in traits:
            tool.selection = self.view.selection
        self.tools = tuple([*self.tools, tool])
        return self

    def refresh(self, sender: object = None) -> asyncio.Task | None:
        """Create asynchronous refresh task which will update the view given any
        changes.

        ``sender`` is ignored; it lets ``refresh`` serve as a tool's ``on_done``
        callback (which receives the tool). Returns ``None`` when no event loop is
        running (see ``Pipe.schedule_run``).
        """
        self.log.debug("Refreshing diagram")
        task = self.pipe.schedule_run()
        if task is None:
            return None
        if task is not self._refresh_task:
            self._refresh_task = task
            task.add_done_callback(self._update_view)
        return task

    def _update_view(self, future: asyncio.Future) -> None:
        """Show the finished layout without replacing the user's inlet tree."""
        try:
            exception = future.exception()
        except asyncio.CancelledError:
            return
        if exception is not None:
            self.log.warning("Diagram refresh failed: %r", exception)
            return
        layout = self.pipe.outlet.value
        if self.view.source is not None:
            self.view.source.value = layout
