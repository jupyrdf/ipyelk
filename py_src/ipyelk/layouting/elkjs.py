# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio
from dataclasses import dataclass, field
from typing import Dict
from uuid import uuid4

import traitlets as T
from ipywidgets import DOMWidget

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..schema import validate_elk_json


@dataclass
class LayoutRequest:
    id: str = field(default_factory=lambda *_: str(uuid4()))
    payload: Dict = field(default_factory=dict)

    def message(self) -> Dict:
        return {
            "id": self.id,
            "payload": self.payload,
        }


class ElkJS(DOMWidget):
    """Jupyterlab widget for interacting with ELK diagrams"""

    _model_name = T.Unicode("ELKLayoutModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._futures = {}
        self.on_msg(self._handle_response)
        self._response_queue = asyncio.Queue()
        self._request_queue = asyncio.Queue()

        asyncio.create_task(self._process_requests())
        asyncio.create_task(self._process_responses())

    @T.default("_value")
    def _default_value(self):
        return {"id": "root"}

    async def layout(self, value):
        future = asyncio.Future()
        request = LayoutRequest(payload=value)
        self._futures[request.id] = future
        try:
            assert validate_elk_json(value)
            await self._request_queue.put(request)
            result = await future
        except Exception as E:
            future.set_exception(E)
            raise E
        finally:
            self._futures.pop(request.id)
        # remove shared reference of the message future
        return result

    async def _process_requests(self):
        """Asyncio task loop to process the input request queue"""
        while True:
            requests = await self._get_request()
            if requests:
                self.send(requests.message())

    async def _get_request(self):
        """Get request from the request queue."""
        return await self._request_queue.get()

    async def _process_responses(self):
        """Asyncio task loop to process the output response queue"""
        while True:
            response = await self._response_queue.get()
            future = self._futures[response["id"]]
            future.set_result(response["payload"])
            self._response_queue.task_done()

    def _handle_response(self, _, content, buffers):
        """Method to process messages back from the browser and resolve measurements"""
        if content.get("event", "") == "layout":
            asyncio.create_task(self._response_queue.put(content))
