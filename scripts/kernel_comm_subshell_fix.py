# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Dispatch a comm message on the subshell its client addressed (ipykernel 7.4).

ipykernel 7.4 routes every comm message to the (sub)shell the kernel last *sent*
on that comm from (``BaseComm._reply_subshell_for``, ipykernel#1565), and only
falls back to the ``subshell_id`` in the message header when the kernel never sent
on the comm. JupyterLab 4.6 sends widget comm messages on a subshell of their own
(``commsOverSubshells``), so a widget's first update after the cell that displayed
it runs on the main shell, the later ones on the subshell, and two widgets' updates
can run on two threads at once.

ipywidgets' ``interact`` wraps every call in ``with out:``. With two such blocks
open on two threads, the inner one's exit does not clear the Output's ``msg_id``
(the outer still holds the count), so the inner message's ``status: idle`` reaches
the page while jupyterlab-manager's Output hook is still registered on it. The hook
swallows the idle, ipywidgets' per-model throttle (``_pending_msgs``) never
releases, and that widget never sends again: the kernel's slider values lag the
browser's for good (#232).

This startup file keeps the routing for answers to requests the kernel sent (they
carry ``content.id``) and otherwise dispatches a comm message where the client
addressed it, as ipykernel 7.3 did. It does nothing on ipykernel 7.3 or older.
"""


def routes_by_last_send(comm_cls):
    """Whether ``comm_cls`` routes comm messages by the kernel's last send (7.4+)."""
    return callable(getattr(comm_cls, "_reply_subshell_for", None))


def request_id_of(data):
    """The ``content.id`` of a comm message, as ipykernel 7.4 keys reply routing."""
    if isinstance(data, dict):
        content = data.get("content")
        if isinstance(content, dict) and isinstance(content.get("id"), str):
            return content["id"]
    return None


def patch_reply_subshell_for(comm_cls):
    """Make ``comm_cls`` honour the client's ``subshell_id`` unless a request matches.

    Return ``False`` and change nothing when ``comm_cls`` does not route by last send.
    """
    if not routes_by_last_send(comm_cls):
        return False
    # a closure, not a module global: the startup file deletes its names at the end
    request_id_of_ = request_id_of

    def _reply_subshell_for(self, data, default):
        request_id = request_id_of_(data)
        with self._reply_subshell_lock:
            if request_id is not None and request_id in self._reply_subshell_ids:
                return self._reply_subshell_ids.pop(request_id)
        return default

    comm_cls._reply_subshell_for = _reply_subshell_for
    return True


def _install():
    try:
        from ipykernel.comm.comm import BaseComm
    except ImportError:
        return
    patch_reply_subshell_for(BaseComm)


if __name__ == "__main__":
    _install()
    del _install, patch_reply_subshell_for, request_id_of, routes_by_last_send
