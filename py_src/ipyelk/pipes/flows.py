# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


class Text:
    text = "label.text"
    size_css = "label.properties.cssClasses-size"
    color_css = "label.properties.cssClasses-colors"
    size = "label.size"
    layout_options = "label.layoutOptions"
    labels = "label.labels"
    hidden = "label.properties.hidden"


class Node:
    size = "node.size"
    children = "node.children"
    size_css = "node.properties.cssClasses-size"
    color_css = "node.properties.cssClasses-colors"
    layout_options = "node.layoutOptions"
    labels = "node.labels"
    edges = "node.edges"
    hidden = "node.properties.hidden"
    ports = "node.ports"


class Edge:
    size_css = "edge.properties.cssClasses-size"
    color_css = "edge.properties.cssClasses-colors"
    layout_options = "edge.layoutOptions"
    labels = "edge.labels"
    route = "edge.sections"
    source = "edge.sources"
    target = "edge.targets"
    hidden = "edge.properties.hidden"


class Port:
    size = "port.size"
    size_css = "port.properties.cssClasses-size"
    color_css = "port.properties.cssClasses-colors"
    layout_options = "port.layoutOptions"
    labels = "port.labels"
    hidden = "port.properties.hidden"


AnySize = ".*.size"
AnyHidden = ".*.hidden"
ColorCSS = ".*.cssClasses-colors"
Anythinglayout = "((?!.*cssClasses-colors).)*"  # exclude matches on css color
Layout = "layout"
New = "new"
