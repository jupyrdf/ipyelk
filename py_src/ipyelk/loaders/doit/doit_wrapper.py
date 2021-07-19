from pathlib import Path

import doit
import ipywidgets as W
import traitlets as T


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


if __name__ == "__main__":
    file = Path("../../../../dodo.py")
    pydoit = PyFileDoit(path=str(file))
    pydoit.tasks


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
