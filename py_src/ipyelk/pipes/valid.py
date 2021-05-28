# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict

import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import EdgeReport, IDReport
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

    async def run(self):
        index: MarkIndex = self.inlet.build_index()
        with index.context:
            self.get_reports(index)
            self.errors = self.collect_errors()
            if self.errors:
                raise ValueError("Inlet value is not valid")
            self.apply_fixes(index)

            value = self.inlet.index.root
            if value is self.outlet.value:
                # force refresh if same instance
                self.outlet._notify_trait("value", None, value)
            else:
                self.outlet.value = value
            self.get_reports(self.outlet.build_index())
            self.errors = self.collect_errors()
            if self.errors:
                raise ValueError("Outlet value is not valid")

    def get_reports(self, index: MarkIndex):
        self.edge_report = index.elements.check_edges()
        self.id_report = index.elements.check_ids(*self.edge_report.orphans)
        self.schema_report = {}  # TODO run elkjson schema validator

    def collect_errors(self) -> Dict:
        errors = {}
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

    def apply_fixes(self, index: MarkIndex):
        root = index.root
        if self.id_report.null_ids and self.fix_null_id:
            self.log.warning(f"fixing {len(self.id_report.null_ids)} ids")
            for el in self.id_report.null_ids:
                el.id = el.get_id()

        if self.edge_report.orphans and self.fix_orphans:
            for el in self.edge_report.orphans:
                root.add_child(el)

        if self.edge_report.lca_mismatch and self.fix_edge_owners:
            for edge, (old, new) in self.edge_report.lca_mismatch.items():
                old.edges.remove(edge)
                if new is None:
                    new = root
                new.edges.append(edge)
