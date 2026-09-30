/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { VNode } from 'snabbdom';
import { describe, expect, it } from 'vitest';

import { Bounds, Point } from 'sprotty-protocol';

import { SChildElementImpl, SGraphImpl } from 'sprotty';

import { ElkModelRenderer } from '../sprotty/renderer';
import { ElkEdge, ElkNode } from '../sprotty/sprotty-model';
import {
  CULLING_ENABLED,
  ShapeView,
  intersectsCanvas,
  shouldCull,
  validCanvasBounds,
} from '../sprotty/views/base';
import { ElkEdgeView } from '../sprotty/views/edge_views';

// `isVisible` reads only the rendering target kind off the renderer.
type RenderContext = Pick<ElkModelRenderer, 'targetKind'>;
const asContext = (ctx: RenderContext) => ctx as ElkModelRenderer;
const main = asContext({ targetKind: 'main' });
const hidden = asContext({ targetKind: 'hidden' });

const CANVAS: Bounds = { x: 0, y: 0, width: 800, height: 600 };
const NO_CANVAS: Bounds = { x: 0, y: 0, width: 0, height: 0 };

/** the concrete view under test: `ShapeView.isVisible`, unmodified */
class TestShapeView extends ShapeView {
  render(): VNode | undefined {
    return undefined;
  }
}

function root(canvasBounds: Bounds): SGraphImpl {
  const graph = new SGraphImpl();
  graph.canvasBounds = canvasBounds;
  graph.zoom = 1;
  graph.scroll = { x: 0, y: 0 };
  return graph;
}

function nodeAt(position: Point, canvasBounds: Bounds = CANVAS): ElkNode {
  const node = new ElkNode();
  node.id = 'n0';
  node.type = 'node';
  node.size = { width: 30, height: 30 };
  node.position = position;
  node.properties = {};
  root(canvasBounds).add(node);
  return node;
}

function nodeIsVisible(position: Point, canvasBounds = CANVAS, context = main) {
  const node = nodeAt(position, canvasBounds);
  return new TestShapeView().isVisible(node as SChildElementImpl & ElkNode, context);
}

function edgeWithRoute(route: Point[], canvasBounds: Bounds = CANVAS): ElkEdge {
  const edge = new ElkEdge();
  edge.id = 'e0';
  edge.type = 'edge';
  edge.sourceId = 'n0';
  edge.targetId = 'n1';
  edge.routingPoints = route;
  edge.properties = {};
  root(canvasBounds).add(edge);
  return edge;
}

function edgeIsVisible(route: Point[], canvasBounds = CANVAS, context = main) {
  return new ElkEdgeView().isVisible(
    edgeWithRoute(route, canvasBounds),
    route,
    context,
  );
}

const OFF_SCREEN: Point[] = [
  { x: 5000, y: 50 },
  { x: 5200, y: 60 },
];

describe('CULLING_ENABLED', () => {
  it('is off, so nothing is culled at any viewport', () => {
    // #170: turning it on needs a viewport-independent export path first
    expect(CULLING_ENABLED).toBe(false);
    expect(shouldCull(CANVAS)).toBe(false);
  });

  it('would still not cull before the canvas size is known', () => {
    // the 0x0 first frame: `canvasBounds` is only set by an action, later
    expect(validCanvasBounds(CANVAS)).toBe(true);
    expect(validCanvasBounds(NO_CANVAS)).toBe(false);
    expect(validCanvasBounds({ x: 0, y: 0, width: 800, height: 0 })).toBe(false);
    expect(validCanvasBounds({ x: 0, y: 0, width: 0, height: 600 })).toBe(false);
    expect(shouldCull(NO_CANVAS)).toBe(false);
  });
});

describe('intersectsCanvas', () => {
  // the geometry both views cull by, once #170 turns culling on
  const box = (x: number, y: number): Bounds => ({ x, y, width: 30, height: 30 });

  it('accepts a box inside the canvas', () => {
    expect(intersectsCanvas(box(50, 50), CANVAS)).toBe(true);
  });

  it('accepts a box overlapping an edge of the canvas', () => {
    expect(intersectsCanvas(box(-20, 590), CANVAS)).toBe(true);
    expect(intersectsCanvas(box(800, 600), CANVAS)).toBe(true);
  });

  it('rejects a box past the canvas', () => {
    expect(intersectsCanvas(box(5000, 50), CANVAS)).toBe(false);
    expect(intersectsCanvas(box(-100, -100), CANVAS)).toBe(false);
  });

  it('accepts a route crossing the canvas between off-screen ends', () => {
    // an edge's whole route is one box: both endpoints can be off-screen
    expect(intersectsCanvas({ x: -500, y: 300, width: 5500, height: 0 }, CANVAS)).toBe(
      true,
    );
  });

  it('rejects everything against a 0x0 canvas', () => {
    // why `shouldCull` has to refuse an unmeasured canvas
    expect(intersectsCanvas(box(50, 50), NO_CANVAS)).toBe(false);
  });
});

describe('ShapeView.isVisible', () => {
  it('draws a node inside the viewport', () => {
    expect(nodeIsVisible({ x: 50, y: 50 })).toBe(true);
  });

  it('draws nodes the viewport does not show', () => {
    expect(nodeIsVisible({ x: 5000, y: 50 })).toBe(true);
    expect(nodeIsVisible({ x: -100, y: -100 })).toBe(true);
  });

  it('draws every node while the canvas size is unknown', () => {
    for (const position of [
      { x: 50, y: 50 },
      { x: 5000, y: 50 },
      { x: -100, y: -100 },
    ]) {
      expect(nodeIsVisible(position, NO_CANVAS)).toBe(true);
    }
  });

  it('draws every node for hidden rendering', () => {
    // the hidden div feeds bounds measurement: never skip anything there
    expect(nodeIsVisible({ x: 5000, y: 50 }, CANVAS, hidden)).toBe(true);
    expect(nodeIsVisible({ x: -100, y: -100 }, CANVAS, hidden)).toBe(true);
  });
});

describe('ElkEdgeView.isVisible', () => {
  it('draws an edge routed inside the viewport', () => {
    expect(
      edgeIsVisible([
        { x: 50, y: 50 },
        { x: 200, y: 200 },
      ]),
    ).toBe(true);
  });

  it('draws edges the viewport does not show', () => {
    expect(edgeIsVisible(OFF_SCREEN)).toBe(true);
    expect(
      edgeIsVisible([
        { x: -400, y: -400 },
        { x: -100, y: -100 },
      ]),
    ).toBe(true);
  });

  it('draws every edge while the canvas size is unknown', () => {
    expect(edgeIsVisible(OFF_SCREEN, NO_CANVAS)).toBe(true);
  });

  it('draws every edge for hidden rendering', () => {
    expect(edgeIsVisible(OFF_SCREEN, CANVAS, hidden)).toBe(true);
  });

  it('draws an edge with no route', () => {
    expect(edgeIsVisible([])).toBe(true);
  });
});
