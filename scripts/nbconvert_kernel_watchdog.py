# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Dump every kernel thread's stack when a notebook cell wedges the kernel.

``nbconvert --execute`` gives up on a cell after ``ExecutePreprocessor.timeout``
seconds, but a kernel whose event loop is starved never answers and never prints
anything, so the job log shows the timeout and nothing else. Seen on the
``oldest`` environments, about one run in five: ``03_App.ipynb``, the cell after
``display(box)``, 1200 s, with the kernel silent.

This file runs as an IPython startup file in the kernels nbconvert launches
(``IPYTHONDIR`` is set by the ``nbconvert--`` task). ``faulthandler`` writes the
stacks from a watchdog thread without the GIL or the event loop, so a busy loop
cannot hide from it. It writes to the kernel's original stderr, which ipykernel
forwards to the job log. The default of 900 s is under the 1200 s cell timeout
and far over any healthy run: the whole example set converts in under a minute,
and each notebook gets its own kernel, so the timer starts fresh per notebook.
"""

import faulthandler
import os
import sys

faulthandler.dump_traceback_later(
    float(os.environ.get("IPYELK_KERNEL_WATCHDOG", "900")),
    repeat=False,
    file=sys.__stderr__,
)
