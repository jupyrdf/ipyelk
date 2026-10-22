/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { VNode } from 'snabbdom';
import { describe, expect, it } from 'vitest';

import { Point } from 'sprotty-protocol';

import { SGraphImpl } from 'sprotty';

import { ElkModelRenderer } from '../sprotty/renderer';
import { ElkEdge, ElkLabel, ElkNode } from '../sprotty/sprotty-model';
import { CullingContext } from '../sprotty/views/base';
import { ElkEdgeView } from '../sprotty/views/edge_views';
import { ElkLabelView, ElkNodeView } from '../sprotty/views/node_views';

// The views consult `isVisible` before drawing (#170 item 3): a mutation that
// drops those calls must fail here, not only in the predicate's own tests.

type RenderContext = CullingContext &
  Pick<ElkModelRenderer, 'hrefID' | 'renderChildren' | 'getConnector'>;

function context(culling: boolean, targetKind: 'main' | 'hidden' = 'main') {
  const ctx: RenderContext = {
    targetKind,
    source: { culling },
    hrefID: () => undefined,
    renderChildren: () => [],
    getConnector: () => undefined,
  };
  return ctx as ElkModelRenderer;
}

const ON = context(true);
const OFF = context(false);
const HIDDEN = context(true, 'hidden');

function root(zoom = 1): SGraphImpl {
  const graph = new SGraphImpl();
  graph.canvasBounds = { x: 0, y: 0, width: 800, height: 600 };
  graph.zoom = zoom;
  graph.scroll = { x: 0, y: 0 };
  return graph;
}

function node(position: Point, zoom = 1): ElkNode {
  const n = new ElkNode();
  n.id = 'n0';
  n.type = 'node';
  n.size = { width: 30, height: 30 };
  n.position = position;
  n.properties = {};
  root(zoom).add(n);
  return n;
}

function label(position: Point, zoom = 1): ElkLabel {
  const l = new ElkLabel();
  l.id = 'l0';
  l.type = 'label';
  l.text = 'text';
  l.size = { width: 40, height: 14 };
  l.position = position;
  l.properties = {};
  root(zoom).add(l);
  return l;
}

function edge(route: Point[], withLabel = false): { edge: ElkEdge; view: ElkEdgeView } {
  const e = new ElkEdge();
  e.id = 'e0';
  e.type = 'edge';
  e.sourceId = 'a';
  e.targetId = 'b';
  e.routingPoints = route;
  e.properties = {};
  root().add(e);
  if (withLabel) {
    e.add(label({ x: 0, y: 0 }));
  }
  // the router is injected in the container; here it returns the route as is
  const view = Object.assign(new ElkEdgeView(), {
    edgeRouterRegistry: { get: () => ({ route: () => route }) },
  });
  return { edge: e, view };
}

const ON_SCREEN: Point = { x: 100, y: 100 };
const OFF_SCREEN: Point = { x: 5000, y: 100 };

describe('ElkNodeView', () => {
  it('draws an on-screen node and skips an off-screen one while culling', () => {
    const view = new ElkNodeView();
    expect(view.render(node(ON_SCREEN), ON)).toBeDefined();
    expect(view.render(node(OFF_SCREEN), ON)).toBeUndefined();
  });

  it('draws an off-screen node while culling is off, or for the hidden render', () => {
    const view = new ElkNodeView();
    expect(view.render(node(OFF_SCREEN), OFF)).toBeDefined();
    expect(view.render(node(OFF_SCREEN), HIDDEN)).toBeDefined();
  });
});

describe('ElkLabelView', () => {
  it('draws an on-screen label and skips an off-screen one while culling', () => {
    const view = new ElkLabelView();
    expect(view.render(label(ON_SCREEN), ON)).toBeDefined();
    expect(view.render(label(OFF_SCREEN), ON)).toBeUndefined();
    expect(view.render(label(OFF_SCREEN), OFF)).toBeDefined();
  });

  it('drops a label too small to read on screen, but never in an export', () => {
    // 14 px tall at zoom 0.1 is 1.4 px: below the 3 px level of detail
    const view = new ElkLabelView();
    expect(view.render(label(ON_SCREEN, 0.1), OFF)).toBeUndefined();
    expect(view.render(label(ON_SCREEN, 0.1), ON)).toBeUndefined();
    expect(view.render(label(ON_SCREEN, 0.1), HIDDEN)).toBeDefined();
    expect(view.render(label(ON_SCREEN, 1), OFF)).toBeDefined();
  });
});

describe('ElkEdgeView', () => {
  const ROUTE_ON = [
    { x: 50, y: 50 },
    { x: 200, y: 200 },
  ];
  const ROUTE_OFF = [
    { x: 5000, y: 50 },
    { x: 5200, y: 60 },
  ];

  function classes(vnode: VNode | undefined): string[] {
    return Object.keys(vnode?.data?.class || {});
  }

  it('draws an on-screen edge and skips an off-screen one while culling', () => {
    const on = edge(ROUTE_ON);
    expect(classes(on.view.render(on.edge, ON))).toContain('elkedge');
    const off = edge(ROUTE_OFF);
    expect(off.view.render(off.edge, ON)).toBeUndefined();
    expect(classes(off.view.render(off.edge, OFF))).toContain('elkedge');
    expect(classes(off.view.render(off.edge, HIDDEN))).toContain('elkedge');
  });

  it('keeps a group for the children of a culled edge', () => {
    // an edge label can sit on screen while the route does not: the group
    // gives the label view its own say
    const off = edge(ROUTE_OFF, true);
    const vnode = off.view.render(off.edge, ON);
    expect(vnode?.sel).toBe('g');
    expect(classes(vnode)).not.toContain('elkedge');
  });
});
