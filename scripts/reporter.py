# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
#
# from https://github.com/robots-from-jupyter/robotframework-jupyterlibrary
#
# Copyright (c) 2020 Robots from Jupyter
# Distributed under the terms of the Modified BSD License.


from datetime import datetime

from doit.reporter import ConsoleReporter

from . import project as P

START = "::group::" if P.INSTALL_ARTIFACT else ""
END = "\n::endgroup::" if P.INSTALL_ARTIFACT else ""

TIMEFMT = "%H:%M:%S"
SKIP = "        "


class GithubActionsReporter(ConsoleReporter):
    _gh_timings = {}

    def execute_task(self, task):
        start = datetime.now()
        title = task.title()
        self._gh_timings[title] = [start]
        self.outstream.write(f"""{START}[{start.strftime(TIMEFMT)}] 🦌  {title}\n""")

    def gh_outtro(self, task, emoji):
        title = task.title()
        start, end = self._gh_timings[title] = [
            *self._gh_timings[title],
            datetime.now(),
        ]
        delta = end - start
        sec = str(delta.seconds).rjust(7)
        self.outstream.write(f"{END}\n[{sec}s] {emoji} {task.title()} {emoji}\n")

    def add_failure(self, task, exception):
        super().add_failure(task, exception)
        self.gh_outtro(task, "⭕")

    def add_success(self, task):
        super().add_success(task)
        self.gh_outtro(task, "🏁 ")

    def skip_uptodate(self, task):
        self.outstream.write(f"{START}[{SKIP}] ⏩  {task.title()}{END}\n")

    skip_ignore = skip_uptodate
