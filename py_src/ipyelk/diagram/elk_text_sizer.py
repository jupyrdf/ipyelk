"""Simple widget to get text size from DOM
"""
import asyncio
import logging

# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T
from ipywidgets import DOMWidget

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION

logger = logging.getLogger()


class ElkTextSizer(DOMWidget):
    """Jupyterlab widget for getting rendered text sizes from the DOM"""

    _model_name = T.Unicode("ELKTextSizerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKTextSizerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    text = T.Unicode().tag(sync=True)
    width = T.Float().tag(sync=True)
    height = T.Float().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.futures = {}
        self.on_msg(self._resolve_measurement)
        self.queue = asyncio.Queue()
        asyncio.ensure_future(self.process_queue())
        self.messages = []

    def _resolve_measurement(self, _, content, buffers):
        """Method to process messages back from the browser and resolve measurements"""
        logger.debug("_resolve_measurement handler")
        self.messages.append(content)
        if content.get("event", "") == "measurement":
            logger.debug(f"measured {content}")
            text = content.pop("text")

            self.futures[text].set_result(content)

    async def a_measure(self, text):
        if text not in self.futures:
            self.futures[text] = asyncio.Future()
            await self.queue.put(text)
        return await self.futures[text]

    def measure(self, text):
        if text not in self.futures:
            self.futures[text] = asyncio.Future()
            self.queue.put_nowait(text)
        return self.futures[text]

    async def process_queue(self):
        while True:
            value = await self.queue.get()
            response = self.futures[value]
            self.send({"text": value})
            await response
            del self.futures[value]
            # wait for expected message to return
            # todo remove trait and use messages
