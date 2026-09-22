/**
 * Copyright (c) 2025 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { describe, expect, it } from 'vitest';

import { Point } from 'sprotty-protocol';

import { SGraphImpl } from 'sprotty';

import { contentBounds, contentExtent } from '../sprotty/export_util';
import { ElkEdge, ElkLabel, ElkNode, ElkPort } from '../sprotty/sprotty-model';

function graph(): SGraphImpl {
  const root = new SGraphImpl();
  root.canvasBounds = { x: 0, y: 0, width: 800, height: 600 };
  root.zoom = 1;
  root.scroll = { x: 0, y: 0 };
  return root;
}

function addNode(root: SGraphImpl, id: string, position: Point, size = 30): ElkNode {
  const node = new ElkNode();
  node.id = id;
  node.type = 'node';
  node.position = position;
  node.size = { width: size, height: size };
  node.properties = {};
  root.add(node);
  return node;
}

function addEdge(root: SGraphImpl, id: string, route: Point[]): ElkEdge {
  const edge = new ElkEdge();
  edge.id = id;
  edge.type = 'edge';
  edge.sourceId = 'a';
  edge.targetId = 'b';
  edge.routingPoints = route;
  edge.properties = {};
  root.add(edge);
  return edge;
}

function addLabel(parent: ElkNode | ElkEdge, id: string, position: Point): ElkLabel {
  const label = new ElkLabel();
  label.id = id;
  label.type = 'label';
  label.text = id;
  label.position = position;
  label.size = { width: 40, height: 10 };
  parent.add(label);
  return label;
}

function addPort(node: ElkNode, id: string, position: Point): ElkPort {
  const port = new ElkPort();
  port.id = id;
  port.type = 'port';
  port.position = position;
  port.size = { width: 10, height: 10 };
  port.properties = {};
  node.add(port);
  return port;
}

describe('contentBounds', () => {
  it('unions every child of the root', () => {
    const root = graph();
    addNode(root, 'a', { x: 10, y: 20 });
    addNode(root, 'b', { x: 400, y: 900 }); // far below the 600px canvas
    expect(contentBounds(root)).toEqual({ x: 10, y: 20, width: 420, height: 910 });
  });

  it('includes a port overhanging its node', () => {
    const root = graph();
    const node = addNode(root, 'a', { x: 10, y: 20 }); // 10..40, 20..50
    addPort(node, 'a.p', { x: -5, y: 25 }); // 5..15, 45..55 once placed
    expect(contentBounds(root)).toEqual({ x: 5, y: 20, width: 35, height: 35 });
  });

  it('includes a node label placed outside its node', () => {
    const root = graph();
    const node = addNode(root, 'a', { x: 100, y: 100 });
    addLabel(node, 'a.l', { x: -10, y: -20 }); // above and left of the node
    expect(contentBounds(root)).toEqual({ x: 90, y: 80, width: 40, height: 50 });
  });

  it('includes an edge label away from its route', () => {
    const root = graph();
    addNode(root, 'a', { x: 0, y: 0 });
    const edge = addEdge(root, 'e0', [
      { x: 30, y: 15 },
      { x: 200, y: 15 },
    ]);
    // an edge defines no coordinate system: ELK places its labels absolutely
    addLabel(edge, 'e0.l', { x: 100, y: 250 });
    expect(contentBounds(root)).toEqual({ x: 0, y: 0, width: 200, height: 260 });
  });

  it('includes an edge route that leaves its endpoints', () => {
    const root = graph();
    addNode(root, 'a', { x: 0, y: 0 });
    addEdge(root, 'e0', [
      { x: 30, y: 15 },
      { x: 30, y: -40 },
      { x: 120, y: 15 },
    ]);
    expect(contentBounds(root)).toEqual({ x: 0, y: -40, width: 120, height: 70 });
  });

  it('ignores an edge with no route', () => {
    const root = graph();
    addNode(root, 'a', { x: 0, y: 0 });
    addEdge(root, 'e0', []); // routeless bounds reduce to NaN
    expect(contentBounds(root)).toEqual({ x: 0, y: 0, width: 30, height: 30 });
  });

  it('is empty for a root with no children', () => {
    expect(contentBounds(graph()).width).toBeLessThan(0);
  });
});

describe('contentExtent', () => {
  it('measures from the origin, where the layout starts', () => {
    const root = graph();
    addNode(root, 'a', { x: 10, y: 20 });
    addNode(root, 'b', { x: 400, y: 900 });
    // not the 420x910 content box: the export's viewBox starts at 0 0
    expect(contentExtent(root)).toEqual({ x: 0, y: 0, width: 430, height: 930 });
  });

  it('covers content the viewport cannot show', () => {
    const root = graph();
    addNode(root, 'a', { x: 5000, y: 50 });
    expect(contentExtent(root).width).toBe(5030);
  });

  it('does not move when the diagram is scrolled or zoomed', () => {
    const root = graph();
    addNode(root, 'a', { x: 10, y: 20 });
    const before = contentExtent(root);
    root.scroll = { x: 400, y: 300 };
    root.zoom = 2.5;
    expect(contentExtent(root)).toEqual(before);
  });

  it('is zero-sized for an empty diagram', () => {
    expect(contentExtent(graph())).toEqual({ x: 0, y: 0, width: 0, height: 0 });
  });
});
