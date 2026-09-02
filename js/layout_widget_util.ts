/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import {
  ElkGraphElement,
  ElkNode,
  ElkProperties,
} from './sprotty/json/elkgraph-json';
export function layoutErrorMessage(error: unknown): { action: 'error'; error: string } {
  return { action: 'error', error: `${error}` };
}

type TProperties = Record<string, ElkProperties | undefined>;
type ElkElementWithChildren = ElkGraphElement & {
  children?: ElkNode[];
  ports?: ElkGraphElement[];
  edges?: ElkGraphElement[];
};

/**
 * Collect the `properties` of every graph element into a map keyed by
 * element id, removing them from the element IN PLACE. elkjs fails to
 * process edge properties that are anything more than simple strings, and it
 * does not need them: they carry ipyelk -> sprotty data (e.g. `cssClasses`),
 * so they are stripped before layout and reapplied afterwards.
 */
export function collectProperties(node: ElkNode): TProperties {
  let props: TProperties = {};

  function strip(node: ElkElementWithChildren) {
    props[node.id] = node.properties;
    delete node['properties'];
    // children
    if (node.children) {
      node.children.map(strip);
    }
    // ports
    if (node.ports) {
      node.ports.map(strip);
    }
    // labels
    if (node.labels) {
      node.labels.map(strip);
    }
    // edges
    if (node.edges) {
      node.edges.map(strip);
    }
  }
  strip(node);
  return props;
}

/** Reapply properties collected by {@link collectProperties} onto a layout result. */
export function applyProperties(node: ElkNode, props: TProperties): ElkNode {
  function apply(node: ElkElementWithChildren) {
    node.properties = props[node.id];

    // children
    if (node.children) {
      node.children.map(apply);
    }
    // ports
    if (node.ports) {
      node.ports.map(apply);
    }
    // labels
    if (node.labels) {
      node.labels.map(apply);
    }
    // edges
    if (node.edges) {
      node.edges.map(apply);
    }
  }
  apply(node);
  return node;
}

/**
 * Prepare a graph for elkjs layout without mutating the caller's graph.
 *
 * {@link collectProperties} strips properties in place; running it directly
 * on the shared inlet value made `ELKLayoutModel.layout()` non-idempotent: a
 * duplicate `run` message or an overlapping refresh laid out an
 * already-stripped graph and pushed a layout carrying no `cssClasses` -- the
 * diagram rendered styled, then flipped to unstyled moments later. Deep
 * copying first keeps the inlet value intact, so `layout()` may run any
 * number of times.
 */
export function prepareGraphForElk(rootNode: ElkNode): {
  graph: ElkNode;
  propmap: TProperties;
} {
  const graph: ElkNode = JSON.parse(JSON.stringify(rootNode));
  return { graph, propmap: collectProperties(graph) };
}
