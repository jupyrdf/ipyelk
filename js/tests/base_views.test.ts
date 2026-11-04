/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { VNode } from 'snabbdom';
import { describe, expect, it, vi } from 'vitest';

import { Bounds, Point } from 'sprotty-protocol';

import { SChildElementImpl, SGraphImpl } from 'sprotty';

import { JLModelSource } from '../sprotty/diagram-server';
import { ElkModelRenderer } from '../sprotty/renderer';
import { ElkEdge, ElkNode } from '../sprotty/sprotty-model';
import {
  CullingContext,
  ShapeView,
  intersectsCanvas,
  shouldCull,
  validCanvasBounds,
} from '../sprotty/views/base';
import { ElkEdgeView } from '../sprotty/views/edge_views';

// `diagram-server` pulls in `tokens`, which reads `window` at import time
vi.mock('../tokens', () => ({ ELK_DEBUG: false }));

// `isVisible` reads the rendering target kind and the source's culling flag.
const asContext = (ctx: CullingContext) => ctx as ElkModelRenderer;
const main = asContext({ targetKind: 'main', source: { culling: false } });
const culling = asContext({ targetKind: 'main', source: { culling: true } });
const hidden = asContext({ targetKind: 'hidden', source: { culling: true } });
/** a renderer with no model source at all, as the unit tests build them */
const sourceless = asContext({ targetKind: 'main' });

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

describe('shouldCull', () => {
  it('is off by default, so nothing is culled at any viewport', () => {
    // #170: turning it on needs a viewport-independent export path first
    expect(new JLModelSource().culling).toBe(false);
    expect(shouldCull(main, CANVAS)).toBe(false);
    expect(shouldCull(sourceless, CANVAS)).toBe(false);
  });

  it('culls for a source that opted in, on a sized canvas', () => {
    expect(shouldCull(culling, CANVAS)).toBe(true);
  });

  it('never culls the hidden bounds-measuring render', () => {
    expect(shouldCull(hidden, CANVAS)).toBe(false);
  });

  it('does not cull before the canvas size is known', () => {
    // the 0x0 first frame: `canvasBounds` is only set by an action, later
    expect(validCanvasBounds(CANVAS)).toBe(true);
    expect(validCanvasBounds(NO_CANVAS)).toBe(false);
    expect(validCanvasBounds({ x: 0, y: 0, width: 800, height: 0 })).toBe(false);
    expect(validCanvasBounds({ x: 0, y: 0, width: 0, height: 600 })).toBe(false);
    expect(shouldCull(culling, NO_CANVAS)).toBe(false);
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

  it('draws nodes the viewport does not show while culling is off', () => {
    expect(nodeIsVisible({ x: 5000, y: 50 })).toBe(true);
    expect(nodeIsVisible({ x: -100, y: -100 })).toBe(true);
  });

  it('skips nodes the viewport does not show while culling is on', () => {
    expect(nodeIsVisible({ x: 50, y: 50 }, CANVAS, culling)).toBe(true);
    expect(nodeIsVisible({ x: 790, y: 590 }, CANVAS, culling)).toBe(true); // overlaps
    expect(nodeIsVisible({ x: 5000, y: 50 }, CANVAS, culling)).toBe(false);
    expect(nodeIsVisible({ x: -100, y: -100 }, CANVAS, culling)).toBe(false);
  });

  it('culls against the camera, not the layout origin', () => {
    // the camera at (4900, 0), zoom 1: the node at x=5000 is on screen now
    const node = nodeAt({ x: 5000, y: 50 });
    (node.root as SGraphImpl).scroll = { x: 4900, y: 0 };
    const view = new TestShapeView();
    expect(view.isVisible(node as SChildElementImpl & ElkNode, culling)).toBe(true);
    (node.root as SGraphImpl).zoom = 0.1; // zoomed out: still on screen
    expect(view.isVisible(node as SChildElementImpl & ElkNode, culling)).toBe(true);
    (node.root as SGraphImpl).scroll = { x: 0, y: 0 };
    (node.root as SGraphImpl).zoom = 1;
    expect(view.isVisible(node as SChildElementImpl & ElkNode, culling)).toBe(false);
  });

  it('draws every node while the canvas size is unknown', () => {
    for (const position of [
      { x: 50, y: 50 },
      { x: 5000, y: 50 },
      { x: -100, y: -100 },
    ]) {
      expect(nodeIsVisible(position, NO_CANVAS, culling)).toBe(true);
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

  it('draws edges the viewport does not show while culling is off', () => {
    expect(edgeIsVisible(OFF_SCREEN)).toBe(true);
    expect(
      edgeIsVisible([
        { x: -400, y: -400 },
        { x: -100, y: -100 },
      ]),
    ).toBe(true);
  });

  it('skips edges the viewport does not show while culling is on', () => {
    expect(edgeIsVisible(OFF_SCREEN, CANVAS, culling)).toBe(false);
    expect(
      edgeIsVisible(
        [
          { x: 50, y: 50 },
          { x: 200, y: 200 },
        ],
        CANVAS,
        culling,
      ),
    ).toBe(true);
    // a route crossing the canvas between two off-screen ends is drawn
    expect(
      edgeIsVisible(
        [
          { x: -500, y: 300 },
          { x: 5000, y: 300 },
        ],
        CANVAS,
        culling,
      ),
    ).toBe(true);
  });

  it('draws every edge while the canvas size is unknown', () => {
    expect(edgeIsVisible(OFF_SCREEN, NO_CANVAS, culling)).toBe(true);
  });

  it('draws every edge for hidden rendering', () => {
    expect(edgeIsVisible(OFF_SCREEN, CANVAS, hidden)).toBe(true);
  });

  it('draws an edge with no route', () => {
    expect(edgeIsVisible([], CANVAS, culling)).toBe(true);
  });
});
