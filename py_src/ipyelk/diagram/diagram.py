# Copyright (c) 2021 Dane Freeman.
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
    :py:class:`~ipyelk.transformers.AbstractTransformer`

    Attributes
    ----------

    transformer: :py:class:`~ipyelk.transformers.AbstractTransformer`
        Transformer to convert source objects into valid elk json value
    viewer: :py:class:`~ipyelk.diagram.viewer.Viewer`

    :param toolbar: Toolar for widget
    """

    source: MarkElementWidget = T.Instance(MarkElementWidget, kw={})

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
        from .flow import DefaultFlow

        progress_bar = self.get_tool(PipelineProgressBar)
        return DefaultFlow(on_progress=progress_bar.update)

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

    @T.observe("pipe", "source")
    def _change_pipe(self, change):
        self._update_view_sources()

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
        if change and change.old:
            for tool in change.old:
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
        matches = [tool for tool in self.tools if type(tool) is tool_type]
        num_matches = len(matches)
        if num_matches > 1:
            raise NotUniqueError(f"Found too many tools with type {tool_type}")
        elif num_matches == 0:
            raise NotFoundError(f"No tool matching type {tool_type}")

        return matches[0]

    def register_tool(self, tool: Tool) -> "Diagram":
        # TODO inject dependencies smarter...
        traits = tool.trait_names()
        if "diagram" in traits:
            tool.diagram = self
        if "selection" in traits:
            tool.selection = self.view.selection
        self.tools = tuple([*self.tools, tool])
        return self

    def refresh(self, change: T.Bunch = None) -> asyncio.Task:
        """Create asynchronous refresh task"""
        self.log.debug("Refreshing diagram")
        task: asyncio.Task = self.pipe.schedule_run()

        def update_view(future: asyncio.Task):
            future.exception()
            layout = self.pipe.outlet.value
            self.view.source.value = layout
            self.pipe.inlet.value = layout
            self.pipe.inlet.flow = tuple()

        task.add_done_callback(update_view)
        return task
