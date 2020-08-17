""" Python Quick Types from JSON Schema

    https://app.quicktype.io/?share=v69WIlc7rT81xJjmW3XY
"""
# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

# flake8: noqa

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

T = TypeVar("T")


def strip_none(result: dict) -> dict:
    return {key: value for key, value in result.items() if value is not None}


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False


def from_dict(f: Callable[[Any], T], x: Any) -> Dict[str, T]:
    assert isinstance(x, dict)
    return {k: f(v) for (k, v) in x.items()}


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def to_float(x: Any) -> float:
    if isinstance(x, int):
        x = float(x)
    assert isinstance(x, float)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x


@dataclass
class Elk:
    pass

    @staticmethod
    def from_dict(obj: Any) -> "Elk":
        assert isinstance(obj, dict)
        return Elk()

    def to_dict(self) -> dict:
        result: dict = {}
        return result


@dataclass
class ELKConstructorArguments:
    algorithms: Optional[List[str]] = None
    defaultLayoutOptions: Optional[Dict[str, str]] = None
    workerUrl: Optional[str] = None

    @staticmethod
    def from_dict(obj: Any) -> "ELKConstructorArguments":
        assert isinstance(obj, dict)
        algorithms = from_union(
            [lambda x: from_list(from_str, x), from_none], obj.get("algorithms")
        )
        defaultLayoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none],
            obj.get("defaultLayoutOptions"),
        )
        workerUrl = from_union([from_str, from_none], obj.get("workerUrl"))
        return ELKConstructorArguments(algorithms, defaultLayoutOptions, workerUrl)

    def to_dict(self) -> dict:
        result: dict = {}
        result["algorithms"] = from_union(
            [lambda x: from_list(from_str, x), from_none], self.algorithms
        )
        result["defaultLayoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.defaultLayoutOptions
        )
        result["workerUrl"] = from_union([from_str, from_none], self.workerUrl)
        return strip_none(result)


@dataclass
class ELKLayoutArguments:
    layoutOptions: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ELKLayoutArguments":
        assert isinstance(obj, dict)
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        return ELKLayoutArguments(layoutOptions)

    def to_dict(self) -> dict:
        result: dict = {}
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        return strip_none(result)


@dataclass
class ElkPoint:
    x: float
    y: float

    @staticmethod
    def from_dict(obj: Any) -> "ElkPoint":
        assert isinstance(obj, dict)
        x = from_float(obj.get("x"))
        y = from_float(obj.get("y"))
        return ElkPoint(x, y)

    def to_dict(self) -> dict:
        result: dict = {}
        result["x"] = to_float(self.x)
        result["y"] = to_float(self.y)
        return strip_none(result)


@dataclass
class ElkGraphElement:
    id: str
    labels: Optional[List] = None
    layoutOptions: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkGraphElement":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        return ElkGraphElement(id, labels, layoutOptions)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        return strip_none(result)


@dataclass
class ElkShape(ElkGraphElement):
    id: str
    height: Optional[float] = None
    labels: Optional[List] = None
    layoutOptions: Optional[Dict[str, str]] = None
    width: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkShape":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        height = from_union([from_float, from_none], obj.get("height"))
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        width = from_union([from_float, from_none], obj.get("width"))
        x = from_union([from_float, from_none], obj.get("x"))
        y = from_union([from_float, from_none], obj.get("y"))
        return ElkShape(id, height, labels, layoutOptions, width, x, y)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["height"] = from_union([to_float, from_none], self.height)
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["width"] = from_union([to_float, from_none], self.width)
        result["x"] = from_union([to_float, from_none], self.x)
        result["y"] = from_union([to_float, from_none], self.y)
        return strip_none(result)


@dataclass
class ElkLabel(ElkShape):
    id: str
    text: str = ""
    height: Optional[float] = None
    labels: Optional[List["ElkLabel"]] = None
    layoutOptions: Optional[Dict[str, str]] = None
    width: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkLabel":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        text = from_str(obj.get("text"))
        height = from_union([from_float, from_none], obj.get("height"))
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        width = from_union([from_float, from_none], obj.get("width"))
        x = from_union([from_float, from_none], obj.get("x"))
        y = from_union([from_float, from_none], obj.get("y"))
        return ElkLabel(id, text, height, labels, layoutOptions, width, x, y)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["text"] = from_str(self.text)
        result["height"] = from_union([to_float, from_none], self.height)
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["width"] = from_union([to_float, from_none], self.width)
        result["x"] = from_union([to_float, from_none], self.x)
        result["y"] = from_union([to_float, from_none], self.y)
        return strip_none(result)


@dataclass
class ElkEdge(ElkGraphElement):
    id: str
    junctionPoints: Optional[List[ElkPoint]] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkEdge":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        junctionPoints = from_union(
            [lambda x: from_list(ElkPoint.from_dict, x), from_none],
            obj.get("junctionPoints"),
        )
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        return ElkEdge(id, junctionPoints, labels, layoutOptions)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["junctionPoints"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkPoint, x), x), from_none],
            self.junctionPoints,
        )
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        return strip_none(result)


@dataclass
class ElkEdgeSection(ElkGraphElement):
    id: str
    endPoint: ElkPoint = None
    startPoint: ElkPoint = None
    bendPoints: Optional[List[ElkPoint]] = None
    incomingSections: Optional[List[str]] = None
    incomingShape: Optional[str] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[Dict[str, str]] = None
    outgoingSections: Optional[List[str]] = None
    outgoingShape: Optional[str] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkEdgeSection":
        assert isinstance(obj, dict)
        endPoint = ElkPoint.from_dict(obj.get("endPoint"))
        id = from_str(obj.get("id"))
        startPoint = ElkPoint.from_dict(obj.get("startPoint"))
        bendPoints = from_union(
            [lambda x: from_list(ElkPoint.from_dict, x), from_none],
            obj.get("bendPoints"),
        )
        incomingSections = from_union(
            [lambda x: from_list(from_str, x), from_none], obj.get("incomingSections")
        )
        incomingShape = from_union([from_str, from_none], obj.get("incomingShape"))
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        outgoingSections = from_union(
            [lambda x: from_list(from_str, x), from_none], obj.get("outgoingSections")
        )
        outgoingShape = from_union([from_str, from_none], obj.get("outgoingShape"))
        return ElkEdgeSection(
            endPoint,
            id,
            startPoint,
            bendPoints,
            incomingSections,
            incomingShape,
            labels,
            layoutOptions,
            outgoingSections,
            outgoingShape,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["endPoint"] = to_class(ElkPoint, self.endPoint)
        result["id"] = from_str(self.id)
        result["startPoint"] = to_class(ElkPoint, self.startPoint)
        result["bendPoints"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkPoint, x), x), from_none],
            self.bendPoints,
        )
        result["incomingSections"] = from_union(
            [lambda x: from_list(from_str, x), from_none], self.incomingSections
        )
        result["incomingShape"] = from_union([from_str, from_none], self.incomingShape)
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["outgoingSections"] = from_union(
            [lambda x: from_list(from_str, x), from_none], self.outgoingSections
        )
        result["outgoingShape"] = from_union([from_str, from_none], self.outgoingShape)
        return strip_none(result)


@dataclass
class ElkExtendedEdge(ElkEdge):
    id: str
    sections: Optional[List[ElkEdgeSection]] = None
    sources: Optional[List[str]] = None
    targets: Optional[List[str]] = None
    junctionPoints: Optional[List[ElkPoint]] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[Dict[str, str]] = None
    properties: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkExtendedEdge":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        sections = from_list(ElkEdgeSection.from_dict, obj.get("sections"))
        sources = from_list(from_str, obj.get("sources"))
        targets = from_list(from_str, obj.get("targets"))
        junctionPoints = from_union(
            [lambda x: from_list(ElkPoint.from_dict, x), from_none],
            obj.get("junctionPoints"),
        )
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        properties = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("properties")
        )
        return ElkExtendedEdge(
            id,
            sections,
            sources,
            targets,
            junctionPoints,
            labels,
            layoutOptions,
            properties,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        if self.sections is not None:
            result["sections"] = from_list(
                lambda x: to_class(ElkEdgeSection, x), self.sections
            )
        result["sources"] = from_list(from_str, self.sources)
        result["targets"] = from_list(from_str, self.targets)
        result["junctionPoints"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkPoint, x), x), from_none],
            self.junctionPoints,
        )
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["properties"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.properties
        )
        return strip_none(result)


@dataclass
class ElkPort(ElkShape):
    id: str
    height: Optional[float] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[Dict[str, str]] = None
    width: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    properties: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkPort":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        height = from_union([from_float, from_none], obj.get("height"))
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        properties = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("properties")
        )
        width = from_union([from_float, from_none], obj.get("width"))
        x = from_union([from_float, from_none], obj.get("x"))
        y = from_union([from_float, from_none], obj.get("y"))
        return ElkPort(id, height, labels, layoutOptions, width, x, y, properties)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["height"] = from_union([to_float, from_none], self.height)
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["properties"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.properties
        )
        result["width"] = from_union([to_float, from_none], self.width)
        result["x"] = from_union([to_float, from_none], self.x)
        result["y"] = from_union([to_float, from_none], self.y)
        return strip_none(result)


@dataclass
class ElkNode(ElkShape):
    id: str
    children: Optional[List["ElkNode"]] = None
    edges: Optional[List[ElkEdge]] = None
    height: Optional[float] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[Dict[str, str]] = None
    ports: Optional[List[ElkPort]] = None
    width: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    properties: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkNode":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        children = from_union(
            [lambda x: from_list(ElkNode.from_dict, x), from_none], obj.get("children")
        )
        edges = from_union(
            [lambda x: from_list(ElkEdge.from_dict, x), from_none], obj.get("edges")
        )
        height = from_union([from_float, from_none], obj.get("height"))
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        properties = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("properties")
        )
        ports = from_union(
            [lambda x: from_list(ElkPort.from_dict, x), from_none], obj.get("ports")
        )
        width = from_union([from_float, from_none], obj.get("width"))
        x = from_union([from_float, from_none], obj.get("x"))
        y = from_union([from_float, from_none], obj.get("y"))
        return ElkNode(
            id,
            children,
            edges,
            height,
            labels,
            layoutOptions,
            properties,
            ports,
            width,
            x,
            y,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["children"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkNode, x), x), from_none],
            self.children,
        )
        result["edges"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkEdge, x), x), from_none],
            self.edges,
        )
        result["height"] = from_union([to_float, from_none], self.height)
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["properties"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.properties
        )
        result["ports"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkPort, x), x), from_none],
            self.ports,
        )
        result["width"] = from_union([to_float, from_none], self.width)
        result["x"] = from_union([to_float, from_none], self.x)
        result["y"] = from_union([to_float, from_none], self.y)
        return strip_none(result)


@dataclass
class ElkPrimitiveEdge(ElkEdge):
    id: str
    source: str = ""
    target: str = ""
    bendPoints: Optional[List[ElkPoint]] = None
    junctionPoints: Optional[List[ElkPoint]] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[Dict[str, str]] = None
    sourcePoint: Optional[ElkPoint] = None
    sourcePort: Optional[str] = None
    targetPoint: Optional[ElkPoint] = None
    targetPort: Optional[str] = None
    properties: Optional[Dict[str, str]] = None

    @staticmethod
    def from_dict(obj: Any) -> "ElkPrimitiveEdge":
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        source = from_str(obj.get("source"))
        target = from_str(obj.get("target"))
        bendPoints = from_union(
            [lambda x: from_list(ElkPoint.from_dict, x), from_none],
            obj.get("bendPoints"),
        )
        junctionPoints = from_union(
            [lambda x: from_list(ElkPoint.from_dict, x), from_none],
            obj.get("junctionPoints"),
        )
        labels = from_union(
            [lambda x: from_list(ElkLabel.from_dict, x), from_none], obj.get("labels")
        )
        layoutOptions = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("layoutOptions")
        )
        sourcePoint = from_union(
            [ElkPoint.from_dict, from_none], obj.get("sourcePoint")
        )
        sourcePort = from_union([from_str, from_none], obj.get("sourcePort"))
        targetPoint = from_union(
            [ElkPoint.from_dict, from_none], obj.get("targetPoint")
        )
        targetPort = from_union([from_str, from_none], obj.get("targetPort"))
        properties = from_union(
            [lambda x: from_dict(from_str, x), from_none], obj.get("properties")
        )
        return ElkPrimitiveEdge(
            id,
            source,
            target,
            bendPoints,
            junctionPoints,
            labels,
            layoutOptions,
            sourcePoint,
            sourcePort,
            targetPoint,
            targetPort,
            properties,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["source"] = from_str(self.source)
        result["target"] = from_str(self.target)
        result["bendPoints"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkPoint, x), x), from_none],
            self.bendPoints,
        )
        result["junctionPoints"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkPoint, x), x), from_none],
            self.junctionPoints,
        )
        result["labels"] = from_union(
            [lambda x: from_list(lambda x: to_class(ElkLabel, x), x), from_none],
            self.labels,
        )
        result["layoutOptions"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.layoutOptions
        )
        result["sourcePoint"] = from_union(
            [lambda x: to_class(ElkPoint, x), from_none], self.sourcePoint
        )
        result["sourcePort"] = from_union([from_str, from_none], self.sourcePort)
        result["targetPoint"] = from_union(
            [lambda x: to_class(ElkPoint, x), from_none], self.targetPoint
        )
        result["targetPort"] = from_union([from_str, from_none], self.targetPort)
        result["properties"] = from_union(
            [lambda x: from_dict(from_str, x), from_none], self.properties
        )
        return strip_none(result)
