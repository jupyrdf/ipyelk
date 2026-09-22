# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import EdgeReport, IDReport, Node
from . import flows as F
from .base import Pipe
from .marks import MarkIndex


class ValidationPipe(Pipe):
    observes = TypedTuple(T.Unicode(), default_value=(F.New,))
    reports = TypedTuple(T.Unicode(), default_value=(F.Layout,))
    fix_null_id = T.Bool(default_value=True)
    fix_edge_owners = T.Bool(default_value=True)
    fix_orphans = T.Bool(default_value=True)
    id_report = T.Instance(IDReport, kw={})
    edge_report = T.Instance(EdgeReport, kw={})
    schema_report = T.Dict(kw={})
    errors = T.Dict(kw={})

    async def run(self) -> None:
        inlet = self.inlet
        if (
            inlet.index.elements is not None
            and inlet.value is not None
            and inlet.value is inlet.index.merged_from
            and inlet.value is not inlet.index.root
        ):
            # A caller swapped the browser's laid-out copy into the inlet
            # (``inlet.value = outlet.value``, as ``Diagram.refresh`` did before
            # 2.1.3).  That copy has no hidden elements and none of the user's
            # objects; the indexed root is the user's tree and already carries
            # the geometry ``persist`` merged, so validate that instead.
            self.log.warning(
                "Inlet value is the browser copy merged into the index, not the "
                "indexed root; validating the indexed hierarchy instead"
            )
            inlet.value = inlet.index.root
        # report ids before any are assigned: `fix_null_id` decides (apply_fixes)
        index: MarkIndex = inlet.build_index(assign_ids=False)
        with index.context:
            self.get_reports(index)
            self.errors = self.collect_errors()
            if self.errors:
                raise ValueError("Inlet value is not valid")
            value, fixes = self.apply_fixes(index)

            if value is self.outlet.value:
                # force refresh if same instance
                self.outlet._notify_trait("value", None, value)
            else:
                self.outlet.value = value
            # the outlet index is always rebuilt (it is the downstream
            # authority and pins assigned ids), but re-reporting on it only
            # tells us something new when a fix moved or added an element
            outlet_index = self.outlet.build_index()
            if fixes:
                self.get_reports(outlet_index)
                self.errors = self.collect_errors()
                if self.errors:
                    raise ValueError("Outlet value is not valid")

    def get_reports(self, index: MarkIndex):
        if index.elements is None:
            raise ValueError("Mark index has no elements")
        self.edge_report, self.id_report = index.elements.get_reports()

    def collect_errors(self) -> dict:
        errors: dict[str, object] = {}
        if self.id_report.duplicated:
            errors["Nonunique Element Ids"] = self.id_report.duplicated

        if self.id_report.null_ids and not self.fix_null_id:
            errors["Null Id Elements"] = self.id_report.null_ids

        if self.edge_report.orphans and not self.fix_orphans:
            errors["Orphan Nodes"] = self.edge_report.orphans

        if self.edge_report.lca_mismatch and not self.fix_edge_owners:
            errors["Lowest Common Ancestor Mismatch"] = self.edge_report.lca_mismatch

        if self.schema_report:
            errors["Schema Error"] = self.schema_report
        return errors

    def apply_fixes(self, index: MarkIndex) -> tuple[Node, int]:
        """Apply the enabled fixes and return the root and how many were made.

        The count is what lets :meth:`run` skip re-reporting on an outlet that
        nothing changed.
        """
        root = index.root
        fixes = 0
        if self.id_report.null_ids and self.fix_null_id:
            self.log.warning(f"fixing {len(self.id_report.null_ids)} ids")
            for el in self.id_report.null_ids:
                el.id = el.get_id()
                fixes += 1

        if self.edge_report.orphans and self.fix_orphans:
            for el in self.edge_report.orphans:
                root.add_child(el)
                fixes += 1

        if self.edge_report.lca_mismatch and self.fix_edge_owners:
            for edge, (old, new) in self.edge_report.lca_mismatch.items():
                old.edges.remove(edge)
                if new is None:
                    new = root
                new.edges.append(edge)
                fixes += 1
        return root, fixes
