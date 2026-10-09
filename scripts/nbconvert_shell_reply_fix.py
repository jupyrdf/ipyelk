# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Send ipykernel 7's shell replies through the shell stream, not raw on its socket.

ipykernel 7.0 to 7.3 read shell requests through a ``ZMQStream`` on the shell
channel thread, but write replies raw on the same ROUTER socket
(``SubshellManager._send_on_shell_channel``). A raw send runs the ``libzmq`` command
processing, which can consume the socket's edge-triggered wake-up. A request that
lands during that send then sits unread while the kernel idles, and the client
times out waiting for its reply (#177, ipykernel#1554 upstream).

In ``nbconvert --execute`` the requests cross when a cell prints into an
``ipywidgets.Output``: ``nbclient`` answers with a ``comm_msg`` on the shell channel
just as the cell's ``execute_reply`` goes out, and the next cell's request strands
behind it.

ipykernel 7.4 fixed this (ipykernel#1529), but requires Python 3.11 or
newer, so the oldest test environment cannot have it. This file backports that fix
as an IPython startup file in the kernels the ``nbconvert--`` task launches, and
does nothing on ipykernel 7.4 or newer.
"""


def patch_send_on_shell_channel(manager_cls, shell_stream):
    """Make ``manager_cls`` send replies through ``shell_stream``.

    Return ``False`` and change nothing when ``manager_cls`` already takes the
    stream (ipykernel 7.4 or newer).
    """
    import inspect

    if "shell_stream" in inspect.signature(manager_cls.__init__).parameters:
        return False

    def _send_on_shell_channel(self, msg):
        shell_stream.send_multipart(msg)

    manager_cls._send_on_shell_channel = _send_on_shell_channel
    return True


def _install():
    from IPython import get_ipython

    try:
        from ipykernel.subshell_manager import SubshellManager
    except ImportError:
        return
    kernel = getattr(get_ipython(), "kernel", None)
    thread = getattr(kernel, "shell_channel_thread", None)
    if thread is None or kernel.shell_stream is None:
        return
    # the manager binds its callbacks when created, in ``kernel.start()``, which runs
    # after the startup files
    if getattr(thread, "_manager", None) is None:
        patch_send_on_shell_channel(SubshellManager, kernel.shell_stream)


if __name__ == "__main__":
    _install()
    del _install, patch_send_on_shell_channel
