# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from pathlib import Path

import doit
import ipywidgets as W
import networkx as nx
import traitlets as T

import ipyelk
import ipyelk.diagram.layout_options as opts
import ipyelk.nx
from ipyelk.diagram.elk_model import ElkLabel, ElkNode, ElkRoot
from ipyelk.tools import tools


def relative(paths, root):
    """Utility function to convert a list of potentially absolute paths to be
    relative to a given root
    """
    for f in paths:
        Path(f)
    results = []
    for f in paths:
        path = Path(f)
        if path.is_absolute():
            path = path.relative_to(root)
        results.append(str(path))

    return results


class Doit(W.Widget):
    doit_ = T.Instance(doit.doit_cmd.DoitMain)
    tasks = W.trait_types.TypedTuple(trait=T.Instance(doit.task.Task))

    @T.observe("doit_")
    def on_doit_change(self, change):
        cmds = self.doit_.get_cmds()
        tasks = self.doit_.task_loader.load_tasks(cmds["list"], None)
        tc = doit.control.TaskControl(tasks)
        self.tasks = tuple(tc.tasks.values())


class FileDoit(Doit):
    path = T.Unicode("dodo.py").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_path_change(T.Bunch(new=self.path))

    @T.observe("path")
    def _on_path_change(self, change):
        self.on_path_change(change)

    def on_path_change(self, change):
        pass


class PyFileDoit(FileDoit):
    def on_path_change(self, change=None):
        self.doit_ = doit.doit_cmd.DoitMain(
            doit.cmd_base.ModuleTaskLoader(doit.loader.get_module(self.path))
        )


class DoElk(W.VBox):
    app = T.Instance(ipyelk.Elk)
    _doit = T.Instance(PyFileDoit)
    root = T.Instance(Path)
    tasks = W.trait_types.TypedTuple(trait=T.Instance(doit.task.Task))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = {"height": "100%"}

        # TODO bookeeping if doit changes
        T.dlink((self._doit, "tasks"), (self, "tasks"))

        self.children = [self.app]

    @T.default("_doit")
    def _default_doit(self):
        doit = PyFileDoit(path=str(self.root / "dodo.py"))
        return doit

    @T.observe("root")
    def _update_doit(self, change=None):
        self._doit.path = str(self.root / "dodo.py")

    @T.default("app")
    def _default_app(self):
        node_layoutopts = opts.OptionsWidget(
            identifier=ElkNode,
            options=[
                opts.PortLabelPlacement(),
                opts.NodeSizeConstraints(),
                opts.PortSide(),
                opts.PortConstraints(value="FIXED_SIDE"),
            ],
        )

        parents_layoutopts = opts.OptionsWidget(
            identifier="parents",
            options=[opts.HierarchyHandling(), opts.EdgeRouting(value="ORTHOGONAL")],
        )
        label_layoutopts = opts.OptionsWidget(
            identifier=ElkLabel, options=[opts.NodeLabelPlacement(horizontal="center")]
        )
        root_layout = opts.OptionsWidget(
            options=[
                parents_layoutopts,
                node_layoutopts,
                label_layoutopts,
            ]
        )

        xelk = ipyelk.nx.XELK(layouts={ElkRoot: root_layout.value})

        app = ipyelk.Elk(
            transformer=xelk,
            layout=dict(height="100%"),
            style={
                " .sprotty rect.elknode": {
                    "stroke-width": "3px",
                },
                " .sprotty .dodo_file > rect.elknode": {
                    "stroke": "rgba(15, 153, 96)",
                },
                " .sprotty .dodo_task > rect.elknode": {
                    "stroke": "rgb(153,15,15)",
                },
            },
        )

        app.toolbar.commands = [
            tools.FitBtn(app=app),
            tools.ToggleCollapsedBtn(app=app),
        ]
        return app

    @property
    def transformer(self):
        return self.app.transformer

    @T.observe("tasks")
    def _update_diagram(self, change=None):
        graph = nx.MultiDiGraph()
        tree = nx.DiGraph()

        in_port = {opts.PortSide.identifier: opts.PortSide(value="WEST").value}
        out_port = {opts.PortSide.identifier: opts.PortSide(value="EAST").value}

        tasks = self.tasks
        targets = {}
        for task in tasks:
            for t in relative(task.targets, self.root):
                if t in targets:
                    raise KeyError("Duplicated target")
                targets[t] = task

        for t in tasks:
            task_id = t.name
            ports = []

            # relative file dependencies
            for f in relative(t.file_dep, self.root):
                dep_id = f
                port_id = f"{task_id}.{f}"

                ports.append(
                    {
                        "id": port_id,
                        "labels": [
                            {
                                "id": f"{port_id}__label",
                                "text": "/".join(f.split("/")[-2::]),
                            }
                        ],
                        "layoutOptions": in_port,
                    }
                )

                if f in targets:
                    source_task = targets[f].name
                    graph.add_edge(
                        source_task, task_id, sourcePort=f, targetPort=dep_id
                    )
                else:
                    # file dependency outside of doit
                    graph.add_node(dep_id, properties={"cssClasses": "dodo_file"})
                    graph.add_edge(
                        dep_id, task_id, sourcePort="exists", targetPort=dep_id
                    )

            for f in relative(t.targets, self.root):
                dep_id = f
                port_id = f"{task_id}.{f}"

                ports.append(
                    {
                        "id": port_id,
                        "labels": [
                            {
                                "id": f"{port_id}__label",
                                "text": "/".join(f.split("/")[-2::]),
                            }
                        ],
                        "layoutOptions": out_port,
                    }
                )
            #         graph.add_edge(task_id, dep_id, sourcePort=dep_id)

            graph.add_node(t.name, ports=ports, properties={"cssClasses": "dodo_task"})

            if ":" in t.name:
                namespaces = t.name.split(":")
                parent = namespaces[0]
                for i, lvl in enumerate(namespaces[1:]):
                    if parent not in graph:
                        graph.add_node(parent, properties={"cssClasses": "dodo_task"})
                    child = ":".join([parent, lvl])
                    tree.add_edge(parent, child)
                    parent = child
        self.transformer.source = (graph, tree)
        self.transformer.refresh()
