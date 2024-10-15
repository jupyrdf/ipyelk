# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import asyncio
from typing import List, Tuple, Type

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
    view: :py:class:`~ipyelk.diagram.viewer.Viewer`
        output view that will render the pipe outlet
    tools: tuple :py:class:`~ipyelk.tools.Tool`
        list of tools that a user of the diagram might use to manipulate the
        state of the diagram.
    symbols: :py:class:`~ipyelk.elements.SymbolSpec`
        additional shape definitions that can be used in rendering the diagram.
        For example unique arrow head shapes or custom node shapes.

    """

    source: MarkElementWidget = T.Instance(
        MarkElementWidget, kw={}, help="Syncs Elk JSON Elements"
    )

    pipe: Pipe = T.Instance(Pipe).tag(sync=True, **W.widget_serialization)
    view: Viewer = T.Instance(Viewer).tag(sync=True, **W.widget_serialization)
    tools: Tuple[Tool] = W.trait_types.TypedTuple(T.Instance(Tool)).tag(
        sync=True, **W.widget_serialization
    )
    toolbar: Toolbar = T.Instance(Toolbar, kw={})
    symbols: SymbolSpec = T.Instance(SymbolSpec, kw={}).tag(
        sync=True, **symbol_serialization
    )

    def __init__(self, *args, **kwargs):
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
        from .flow import BrowserTextSizer, DefaultFlow

        progress_bar = self.get_tool(PipelineProgressBar)
        pipeline = DefaultFlow(on_progress=progress_bar.update)
        for pipe in pipeline.pipes:
            if isinstance(pipe, BrowserTextSizer):
                W.dlink((self, "style"), (pipe, "style"))
        return pipeline

    @T.observe("view")
    def _update_children(self, change: T.Bunch = None):
        """Handle if the viewer instance changes by reobserving handler
        functions

        :param change: viewer change event
        """
        # TODO should the `viewer` instance be allowed to change?
        self._update_view_sources()
        self.children = [self.view, self.toolbar]

    def _update_view_sources(self):
        self.source.flow = (F.New,)
        self.pipe.inlet = self.source
        self.view.source = self.pipe.outlet

    @T.observe("pipe", "source", "style")
    def _change_pipe(self, change):
        self._update_view_sources()
        self.refresh()

    @T.default("tools")
    def _default_tools(self) -> List[Tool]:
        return [
            self.view.selection,
            self.view.fit_tool,
            self.view.center_tool,
            ToggleCollapsedTool(selection=self.view.selection),
            PipelineProgressBar(),
        ]

    @T.observe("tools")
    def _update_tools(self, change=None):
        if change and isinstance(change.old, tuple):
            for tool in change.old or []:
                tool.tee = None
                tool.on_done = None

        for tool in self.tools:
            tool.tee = self.pipe
            tool.on_done = self.refresh

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

    def register_tool(self, tool: Tool) -> "Diagram":
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

    def refresh(self, change: T.Bunch = None) -> asyncio.Task:
        """Create asynchronous refresh task which will update the view given any
        changes.
        """
        self.log.debug("Refreshing diagram")
        task: asyncio.Task = self.pipe.schedule_run()

        def update_view(future: asyncio.Task):
            try:
                future.exception()
            except asyncio.CancelledError:
                pass
            except Exception as E:
                raise E
            layout = self.pipe.outlet.value
            self.view.source.value = layout
            self.pipe.inlet.value = layout
            self.pipe.inlet.flow = tuple()

        task.add_done_callback(update_view)
        return task
