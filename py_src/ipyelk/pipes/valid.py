# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from pydantic.networks import int_domain_regex
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple
from typing import Dict

from ..elements import BaseElement, ElementIndex, EdgeReport, IDReport, convert_elkjson
from . import flows as F
from .base import Pipe


class ValidationPipe(Pipe):

    observes = TypedTuple(T.Unicode(), default_value=(F.Anythinglayout,))
    reports = TypedTuple(T.Unicode(), default_value=(F.Layout,))
    fix_null_id = T.Bool(default_value=True)
    fix_edge_owners = T.Bool(default_value=True)
    fix_orphans = T.Bool(default_value=True)
    id_report = T.Instance(IDReport, kw={})
    edge_report = T.Instance(EdgeReport, kw={})
    schema_report = T.Dict(kw={})
    errors = T.Dict(kw={})

    async def run(self):
        with self.inlet.index.context:
            self.get_reports()
            self.errors = self.collect_errors()
            if self.errors:
                raise ValueError("Inlet value is not valid")
            self.apply_fixes()
            self.inlet.build_index()
            self.outlet.value = self.inlet.index.root

    def get_reports(self):
        element_index: ElementIndex = self.inlet.build_index()
        self.edge_report = element_index.check_edges()
        self.id_report = element_index.check_ids(*self.edge_report.orphans)
        self.schema_report = {}  # TODO run elkjson schema validator

    def collect_errors(self)->Dict:
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

    def apply_fixes(self):
        index = self.inlet.index

        if self.id_report.null_ids and self.fix_null_id:
            self.log.warning(f"fixing {len(self.id_report.null_ids)} ids")
            for el in self.id_report.null_ids:
                el.id = el.get_id()
        root = index.root
        if self.edge_report.orphans and self.fix_orphans:
            for el in self.edge_report.orphans:
                root.add_child(el)

        if self.edge_report.lca_mismatch and not self.fix_edge_owners:
            for edge, (old, new) in self.edge_report.lca_mismatch.items():
                old.edges.remove(edge)
                if new is None:
                    new = root
                new.edges.append(edge)
