"""Simple widget to get text size from DOM
"""
# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
from dataclasses import dataclass
from typing import List

import traitlets as T
from ipywidgets import DOMWidget

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION


@dataclass
class TextSize:
    width: float
    height: float


@dataclass
class Text:
    value: str
    css_classes: List[str] = None


class ElkTextSizer(DOMWidget):
    """Jupyterlab widget for getting rendered text sizes from the DOM"""

    _model_name = T.Unicode("ELKTextSizerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKTextSizerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    _request_queue: asyncio.Queue = None
    _response_queue: asyncio.Queue = None

    custom_css = T.List()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.futures = {}
        self.on_msg(self._handle_response)
        self._response_queue = asyncio.Queue()
        self._request_queue = asyncio.Queue()

        asyncio.create_task(self._process_requests())
        asyncio.create_task(self._process_responses())

    @T.observe("custom_css")
    def _bust_futures_cache(self, change=None):
        pass

    def _handle_response(self, _, content, buffers):
        """Method to process messages back from the browser and resolve measurements"""
        self.log.error(f"_resolve_measurement handler {content}")

        if content.get("event", "") == "measurement":
            for test_size in content.get("measurements"):
                asyncio.create_task(self._response_queue.put(test_size))

    async def measure(self, text: Text) -> TextSize:
        """Measure the given text and return `TextSize` object containing the width and height

        :param text: Text to pass to the browser for sizing
        :type text: str
        :return: Text size object for the measured text
        :rtype: TextSize
        """
        # if instance(test, list):
        #     await asyncio.gather(self.measure(t) for t in texts)

        if text not in self.futures:
            self.futures[text] = asyncio.Future()
            await self._request_queue.put(text)
        return await self.futures[text]

    async def _process_requests(self):
        """Asyncio task loop to process the input request queue"""
        while True:
            self.log.error("About to wait for request")
            texts = await self.get_requests()
            self.log.error(f"Got {len(texts)} request(s) {texts}")
            if texts:
                message = {
                    "texts": [
                        {"value": t.value, "cssClasses": " ".join(t.css_classes)}
                        for t in texts
                    ]
                }
                self.send(message)

    async def get_requests(self, timeout=None, max_size=1) -> List[Text]:
        requests = []

        try:
            while len(requests) < max_size:
                value = await asyncio.wait_for(self._request_queue.get(), timeout)
                if isinstance(value, str):
                    value = Text(value=value, css_classes=[])
                requests.append(value)
                self._request_queue.task_done()
        except asyncio.TimeoutError:
            pass
        return requests

    async def _process_responses(self):
        """Asyncio task loop to process the output response queue"""
        while True:
            self.log.error("About to wait for response")
            response = await self._response_queue.get()
            self.log.error(f"Got a response {response}")
            future = self.futures[response.get("text")]
            future.set_result(
                TextSize(width=response.get("width"), height=response.get("height"),)
            )
            self._response_queue.task_done()
