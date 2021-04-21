# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio
from typing import Optional, Tuple

import ipywidgets as W
import traitlets as T

from ..elements import Mark
from ..exceptions import ElkRegistryError
from ..layouting import ElkJS, LayoutEngine
from ..model.model import ElkNullElement
from ..styled_widget import StyledWidget
from ..transformers import AbstractTransformer
from .toolbar import Toolbar
from .viewer import Viewer


class Diagram(W.VBox, StyledWidget):
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

    data = T.Any(allow_none=True)
    transformer: Optional[AbstractTransformer] = T.Instance(
        AbstractTransformer, allow_none=True
    )
    layoutengine: LayoutEngine = T.Instance(LayoutEngine)
    viewer: Viewer = T.Instance(Viewer, kw={})
    selected: Tuple[Mark] = T.Tuple()
    hovered: Optional[Mark] = T.Any(allow_none=True, default_value=ElkNullElement)
    toolbar: Toolbar = T.Instance(Toolbar, kw={})

    _transformer: Optional[AbstractTransformer] = None
    _task: asyncio.Task = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_children()
        self.add_class("jp-ElkApp")

    @T.default("layoutengine")
    def _default_layoutengine(self) -> LayoutEngine:
        return ElkJS()

    def get_transformer(self) -> AbstractTransformer:
        """Get the current transformer if valid for current data else attempts
        to find a valid on.

        :raises TypeError: If current transformer is not valid for input data type
        :return: transformer instance
        """
        if self.transformer:
            if not self.transformer.check(self.data):
                # TODO should the behavior be to clear the `self.transformer`?
                raise TypeError("Current transformer cannot operate on data type")
            return self.transformer
        # dynamic transformer lookup
        _cls = AbstractTransformer.get_transformer_cls(self.data)
        # TODO test if reuse past transformer?
        # self._transformer
        return _cls()  # TODO init args?

    @T.observe("viewer")
    def _update_children(self, change: T.Bunch = None):
        """Handle if the viewer instance changes by reobserving handler
        functions

        :param change: viewer change event
        """
        # TODO should the `viewer` instance be allowed to change?
        self.children = [self.viewer, self.toolbar]

        if change:
            # uninstall old observers
            safely_unobserve(change.old, "selected")
            safely_unobserve(change.old, "hovered")

        if self.viewer:  # also change.new
            self.viewer.observe(self._handle_selected, "selected")
            self.viewer.observe(self._handle_hovered, "hovered")

    def _handle_selected(self, change: T.Bunch):
        """Handles viewer selection changes by translating the elk ids back
        through the transformer

        :param change: selection change event
        """
        items = []
        if change.new:
            items = [self._transformer.from_id(s) for s in change.new]
        if items != self.selected:
            self.selected = items

    def _handle_hovered(self, change: T.Bunch):
        """Handles viewer hover changes by translating the elk id back
        through the transformer

        :param change: hover change event
        """
        try:
            _id = self._transformer.from_id(change.new)
        except ElkRegistryError:
            _id = ElkNullElement
        if _id != self.hovered:
            self.hovered = _id

    @T.observe("selected")
    def _update_selected(self, change: T.Bunch):
        if not self.viewer:
            return

        # transform selected nodes into ids and test if new ids
        ids = [self._transformer.to_id(s) for s in self.selected]
        if self.viewer.selected != ids:
            self.viewer.selected = ids

    @T.observe("hovered")
    def _update_hover(self, change: T.Bunch):
        if not self.viewer or self.hovered is ElkNullElement:
            return

        # transform hovered nodes into elk id
        try:
            self.viewer.hover = self._transformer.to_id(self.hovered)
        except ElkRegistryError:
            # okay not to pass the hovered state to the diagram?
            pass

    @T.observe("data")
    def refresh(self, change: T.Bunch = None):
        """Create asynchronous refresh task"""
        self.log.debug("Refreshing diagram")
        # remove previous refresh task if still pending
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._arefresh(change))

    async def _arefresh(self, change: T.Bunch = None):
        """[summary]

        :param change: [description], defaults to None
        :type change: T.Bunch, optional
        """
        try:
            transformer = (
                self.get_transformer()
            )  # get the right function based on the data type
            self._transformer = transformer  # handle for hover / selection events
            value = await transformer.transform(self.data)
            layout = await self.layoutengine.layout(value)
            self.viewer.mark_layout = layout
        except Exception as e:
            self.e = e
            self.log.exception(e)
            raise e


def safely_unobserve(item, handler):
    if hasattr(item, "unobserve"):
        item.unobserve(handler=handler)
