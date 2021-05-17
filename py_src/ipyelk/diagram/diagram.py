# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio
from typing import Tuple

import ipywidgets as W
import traitlets as T

# from ..json.util import iter_elements
from ..pipes import MarkElementWidget, Pipe
from ..pipes import flows as F
from ..styled_widget import StyledWidget
from ..tools import ToggleCollapsedTool, Tool
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

    # style = t.Dict()
    source = T.Instance(MarkElementWidget, kw={})

    pipe = T.Instance(Pipe).tag(sync=True, **W.widget_serialization)
    view: Viewer = T.Instance(Viewer).tag(sync=True, **W.widget_serialization)
    tools: Tuple[Tool] = T.List(T.Instance(Tool)).tag(
        sync=True, **W.widget_serialization
    )

    # symbols

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_children()
        self.add_class("jp-ElkApp")

    @T.default("view")
    def _default_view(self):
        return SprottyViewer()

    @T.default("pipe")
    def _default_Pipe(self):
        from .flow import DefaultFlow

        return DefaultFlow()

    def add_tool(self, tool: Tool) -> Tool:
        tool.tee = self.pipe
        tool.on_done = self.refresh
        return tool

    def remove_tool(self, tool: Tool) -> Tool:
        tool.tee = None
        tool.on_done = None
        return tool

    @T.default("tools")
    def _default_tools(self):
        tools = [
            self.view.selection,
            ToggleCollapsedTool(selection=self.view.selection),
        ]
        return [self.add_tool(tool) for tool in tools]

    @T.observe("view")
    def _update_children(self, change: T.Bunch = None):
        """Handle if the viewer instance changes by reobserving handler
        functions

        :param change: viewer change event
        """
        # TODO should the `viewer` instance be allowed to change?
        self._update_view_sources()
        self.children = [
            self.view,
            # self.toolbar
        ]

    def _update_view_sources(self):
        self.source.flow = (F.New,)
        self.pipe.inlet = self.source
        self.view.source = self.pipe.outlet

    @T.observe("pipe", "source")
    def _change_pipe(self, change):
        self._update_view_sources()

    # @T.observe("source")
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
