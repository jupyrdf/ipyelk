"""Widget to get text size from DOM
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import traitlets as T
from async_lru import alru_cache

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from ..styled_widget import StyledWidget
from .elk_model import ElkLabel, ElkProperties


@dataclass
class TextSize:
    width: float
    height: float


@dataclass
class SizingRequest:
    text: ElkLabel
    _id: str = None

    @property
    def id(self) -> str:
        if self._id is None:
            self._id = str(uuid.uuid4())
        return self._id

    def message(self) -> Dict:
        """Build message to send to the frontend with the Text Object and
        message id"""
        css_classes = None
        if self.text.properties:
            css_classes = self.text.properties.cssClasses
        if css_classes is None:
            css_classes = ""
        return {"value": self.text.text, "cssClasses": css_classes, "id": self.id}


class ElkTextSizer(StyledWidget):
    """Jupyterlab widget for getting rendered text sizes from the DOM"""

    _model_name = T.Unicode("ELKTextSizerModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_name = T.Unicode("ELKTextSizerView").tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _view_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)

    _request_queue: asyncio.Queue = None
    _response_queue: asyncio.Queue = None

    timeout = T.Float(default_value=0.1, min=0)
    max_size = T.Int(default_value=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._futures = {}
        self.on_msg(self._handle_response)
        self._response_queue = asyncio.Queue()
        self._request_queue = asyncio.Queue()

        asyncio.create_task(self._process_requests())
        asyncio.create_task(self._process_responses())

    @T.observe("style")
    def _bust_futures_cache(self, change=None):
        self.measure.cache_clear()

    def _handle_response(self, _, content, buffers):
        """Method to process messages back from the browser and resolve measurements"""
        if content.get("event", "") == "measurement":
            for test_size in content.get("measurements"):
                asyncio.create_task(self._response_queue.put(test_size))

    @alru_cache(maxsize=8000)
    async def measure(self, text: Union[ElkLabel, str]) -> TextSize:
        """Measure the given text and return `TextSize` object containing the width and height

        :param text: Text to pass to the browser for sizing
        :type text: Union[Text, str]
        :return: Text size object for the measured text
        :rtype: TextSize
        """

        if isinstance(text, str):
            # go ahead and wrap in Text object
            text = ElkLabel(id=str(uuid.uuid4()), text=text)
        if not isinstance(text, ElkLabel):
            return await asyncio.gather(*[self.measure(t) for t in text])

        # create shared reference of the message future
        request = SizingRequest(text)
        future_response = asyncio.Future()
        self._futures[request.id] = future_response
        await self._request_queue.put(request)
        result = await future_response
        # remove shared reference of the message future
        self._futures.pop(request.id)
        return result

    async def _process_requests(self):
        """Asyncio task loop to process the input request queue"""
        while True:
            requests = await self.get_requests()
            if requests:
                self.send({"texts": [r.message() for r in requests]})

    async def get_requests(self) -> List[ElkLabel]:
        """Get requests from the request queue up to the `max_size` and
        `timeout` limits
        """
        requests = []

        try:
            while len(requests) < self.max_size:
                timeout = None if len(requests) == 0 else self.timeout
                value = await asyncio.wait_for(self._request_queue.get(), timeout)
                requests.append(value)
                self._request_queue.task_done()
        except asyncio.TimeoutError:
            pass
        return requests

    async def _process_responses(self):
        """Asyncio task loop to process the output response queue"""
        while True:
            response = await self._response_queue.get()
            future = self._futures[response["id"]]
            future.set_result(
                TextSize(
                    width=response.get("width"),
                    height=response.get("height"),
                )
            )
            self._response_queue.task_done()


async def size_labels(text_sizer: Optional[ElkTextSizer], labels: List[ElkLabel]):
    """Run a list of ElkLabels through to the TextSizer measurer

    :param labels: [description]
    :type labels: List[ElkLabel]
    :return: Updated Labels
    """
    if text_sizer:
        sizes = await text_sizer.measure(tuple(labels))
    else:
        sizes = [
            TextSize(
                width=10 * len(label.text),
                height=10,  # TODO add height default
            )
            for label in labels
        ]

    for size, label in zip(sizes, labels):
        # recording size in the shape props to backout nested label positions
        shape = {
            "width": size.width,
            "height": size.height,
        }
        if label.properties is None:
            label.properties = ElkProperties(shape=shape)

        if label.properties.shape is None:
            label.properties.shape = shape
        else:
            label.properties.shape.update(shape)

    for label in labels:
        overall = size_nested_label(label)
        label.width = overall["width"]
        label.height = overall["height"]


def size_nested_label(label: ElkLabel):
    shape = label.properties.shape
    size = {
        "width": label.width or shape.get("width", 0),
        "height": label.height or shape.get("height", 0),
    }
    for sublabel in label.labels or []:
        ls = size_nested_label(sublabel)
        spacing = float(
            getattr(sublabel, "layoutOptions", {}).get(
                "org.eclipse.elk.spacing.labelLabel", 0
            )
        )
        size = {
            "width": size["width"] + ls["width"] + spacing,
            "height": max(size["height"], ls["height"]),
        }
    return size
