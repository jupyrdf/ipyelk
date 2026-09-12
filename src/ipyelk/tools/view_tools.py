# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from collections.abc import Iterator

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import BaseElement
from ..exceptions import RemovedAPI
from ..pipes import MarkIndex
from .tool import Tool, ToolButton


class Selection(Tool):
    """Tool exposing the ids and elements for selected marks in the
    diagram.

    ``ids`` is never filtered on assignment: the browser may select ids before the
    first layout has been indexed, and kernel code may select ids it knows are
    coming. Resolution to elements is where unknown ids surface, explicitly.

    Attributes
    ----------
    ids: tuple
    tuple of string ids currently selected.

    """

    ids = TypedTuple(trait=T.Unicode()).tag(sync=True)

    def get_index(self) -> MarkIndex:
        """The attached pipe's element index, built on first use.

        Raises ``ValueError`` when the selection has no ``tee`` to resolve against.
        """
        if self.tee is None:
            raise ValueError("Tool not attached to a pipe")
        inlet = self.tee.inlet
        if inlet.index.elements is None and inlet.value is not None:
            inlet.build_index()  # the MarkIndex always exists; its elements may not
        return inlet.index

    def elements(self, *, strict: bool = True) -> Iterator[BaseElement]:
        """The selected elements, in ``ids`` order.

        :param strict: when True (default) an id the index does not know raises
            :py:class:`~ipyelk.exceptions.NotFoundError` naming it; when False such
            ids are skipped (see :meth:`missing_ids` to report them).
        """
        index = self.get_index()
        if strict:
            yield from map(index.from_id, self.ids)  # ``NotFoundError`` names the id
            return
        missing = set(self.missing_ids())
        yield from (index.from_id(el_id) for el_id in self.ids if el_id not in missing)

    def missing_ids(self) -> tuple[str, ...]:
        """The selected ids the index does not know, in ``ids`` order."""
        known = self.get_index().elements
        if known is None:  # nothing has been indexed yet (no value on the inlet)
            return tuple(self.ids)
        return tuple(el_id for el_id in self.ids if el_id not in known.elements)


class Hover(Tool):
    """Tool exposing the id of the mark under the pointer in the diagram.

    Attributes
    ----------
    hovered_id: str | None
    id of the hovered element, or ``None`` when the pointer is over no element.
    Setting it from the kernel highlights that element; setting ``None`` clears
    the highlight.

    """

    hovered_id = T.Unicode(default_value=None, allow_none=True).tag(sync=True)
    #: removed name; raises :class:`~ipyelk.exceptions.DeprecatedAPIError` through 3.x
    ids = RemovedAPI(
        "Hover.ids was removed in ipyelk 3.0: despite the plural name it only ever "
        "held one id (a str), and it never cleared on pointer leave. Use "
        "hover.hovered_id (str | None; None once the pointer leaves). No alias: this "
        "error is raised throughout 3.x."
    )


class Viewport(Tool):
    """The most recently reported camera of a diagram view, written by the browser.

    A state-only tool (no ``run()``, no ``ui``) reached as ``viewer.viewport``. It is
    the snapshot of the **most recently reporting view**, not a global viewport:
    several views of one diagram stay independent, and each report names the view
    that produced it in ``view_id``. The last report stands when a view disconnects.
    A per-view map may be added later as ``Viewer.viewports``.

    All traits are ``None`` until the first report and read-only in the kernel (the
    browser is the only writer). To move a view, use
    :py:meth:`~ipyelk.diagram.SprottyViewer.set_viewport`; commands and observed
    state travel on different channels, so a command never echoes as a report.

    Attributes
    ----------
    view_id: str | None
    stable id of the view (one rendered output) that produced this snapshot.
    origin: tuple[float, float] | None
    diagram coordinates of the canvas top-left corner (sprotty ``scroll``).
    zoom: float | None
    CSS pixels per diagram unit; ``1.0`` is 1:1.
    canvas_size: tuple[float, float] | None
    size of the diagram's div in CSS pixels.
    viewed_ids: tuple[str, ...] | None
    ids of the model elements whose bounds touch the visible rectangle, in model
    order. Edges are never listed (they have no bounds of their own); neither are
    renderer artifacts (junctions, symbols) nor the slack ports and edges that
    stand in for hidden elements, so a hidden element's id never appears.

    """

    view_id = T.Unicode(default_value=None, allow_none=True, read_only=True).tag(
        sync=True
    )
    origin = T.Tuple(
        T.Float(), T.Float(), default_value=None, allow_none=True, read_only=True
    ).tag(sync=True)
    zoom = T.Float(default_value=None, allow_none=True, read_only=True).tag(sync=True)
    canvas_size = T.Tuple(
        T.Float(), T.Float(), default_value=None, allow_none=True, read_only=True
    ).tag(sync=True)
    viewed_ids = TypedTuple(
        T.Unicode(), default_value=None, allow_none=True, read_only=True
    ).tag(sync=True)


class FitTool(ToolButton):
    description = T.Unicode(default_value="Fit")


class CenterTool(ToolButton):
    description = T.Unicode(default_value="Center")


class SetTool(Tool):
    """Maintain an ``active`` set of elements from the selection (add/set/remove
    buttons); the buttons are disabled until ``selection`` is bound.
    """

    selection = T.Instance(Selection, allow_none=True, default_value=None)
    _dependencies = ("selection",)
    active = TypedTuple(T.Instance(BaseElement), kw={})
    css_classes = TypedTuple(T.Unicode())

    @T.default("css_classes")
    def _default_css_classes(self):
        return tuple([
            "active-set",
        ])

    @T.observe("active")
    def _update_active(self, change: T.Bunch) -> None:
        """Move the ``css_classes`` from the elements leaving ``active`` to the ones
        entering it (a trait observer, not an execution entry point).
        """
        try:
            new = set(change.new)
        except Exception:
            new = set()
        try:
            old = set(change.old)
        except Exception:
            old = set()

        exiting, entering = lifecycle(old, new)

        for el in entering:
            el.add_class(*self.css_classes)
        for el in exiting:
            el.remove_class(*self.css_classes)

    def add(self):
        if self.selection:
            self.active = tuple(set(self.active) | set(self.selection.elements()))
        else:
            self.active = tuple(set(self.active))

    def remove(self):
        if self.selection:
            self.active = tuple(set(self.active) - set(self.selection.elements()))
        else:
            self.active = tuple(set(self.active))

    def set_active(self):
        if self.selection:
            self.active = tuple(set(self.selection.elements()))

    @T.default("ui")
    def _default_ui(self):
        add_btn = W.Button(description="", icon="plus", layout={"width": "2.6em"})
        remove_btn = W.Button(description="", icon="minus", layout={"width": "2.6em"})
        set_btn = W.Button(description="", icon="circle", layout={"width": "2.6em"})

        add_btn.on_click(lambda *_: self.add())
        remove_btn.on_click(lambda *_: self.remove())
        set_btn.on_click(lambda *_: self.set_active())
        return W.HBox([add_btn, set_btn, remove_btn])


def lifecycle(old: set, new: set) -> tuple[set, set]:
    exiting = old.difference(new)
    entering = new.difference(old)
    return exiting, entering
