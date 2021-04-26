# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio


def wait_for_change(widget, value):
    """Pattern from
    https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20Asynchronous.html?highlight=async#Waiting-for-user-interaction
    """

    future = asyncio.Future()

    def getvalue(change):
        # make the new value available
        future.set_result(change.new)
        widget.unobserve(getvalue, value)

    widget.observe(getvalue, value)
    return future
