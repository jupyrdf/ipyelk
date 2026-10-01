/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { describe, expect, it } from 'vitest';

import { SGraphImpl, SNodeImpl, createFeatureSet } from 'sprotty';

import { ElkNode as ElkNodeJson } from '../sprotty/json/elkgraph-json';
import { ElkEdge, ElkNode, ElkPort } from '../sprotty/sprotty-model';
import {
  IViewportReport,
  ViewportReporter,
  intersects,
  modelIds,
  sameReport,
  viewedIds,
  viewportRect,
} from '../viewport_util';

// UNIT tests (node, no browser): a real sprotty model, no DOM, no widget manager.

// What the kernel's VisibilityPipe sends when `hidden` is collapsed: the edge that
// pointed at it now ends on a SLACK PORT that carries the hidden element's id.
const LAYOUT: ElkNodeJson = {
  id: 'root',
  children: [
    { id: 'n1', x: 0, y: 0, width: 60, height: 30, labels: [{ id: 'l1', text: 'n1' }] },
    { id: 'far', x: 1000, y: 1000, width: 60, height: 30 },
    {
      id: 'n2',
      x: 100,
      y: 0,
      width: 60,
      height: 30,
      ports: [
        {
          id: 'hidden',
          x: 55,
          y: 10,
          width: 5,
          height: 5,
          properties: { cssClasses: 'slack-port' },
        },
      ],
    },
  ],
  edges: [
    { id: 'e1', sources: ['n1'], targets: ['n2'] },
    {
      id: 'e2',
      sources: ['n1'],
      targets: ['hidden'],
      properties: { cssClasses: 'slack-edge' },
    },
  ],
};

function node(id: string, x: number, y: number, w = 60, h = 30): ElkNode {
  const n = new ElkNode();
  n.id = id;
  n.type = 'node';
  n.position = { x, y };
  n.size = { width: w, height: h };
  n.features = createFeatureSet(SNodeImpl.DEFAULT_FEATURES);
  return n;
}

/** The sprotty model the ELK -> sprotty transform builds from LAYOUT (+ a junction). */
function model(): SGraphImpl {
  const root = new SGraphImpl();
  root.id = 'root';
  root.add(node('n1', 0, 0));
  root.add(node('far', 1000, 1000));
  const n2 = node('n2', 100, 0);
  root.add(n2);
  const slack = new ElkPort();
  slack.id = 'hidden';
  slack.type = 'port';
  slack.position = { x: 55, y: 10 };
  slack.size = { width: 5, height: 5 };
  n2.add(slack);
  for (const id of ['e1', 'e2']) {
    const edge = new ElkEdge();
    edge.id = id;
    edge.type = 'edge';
    root.add(edge);
  }
  root.add(node('e1_j0', 80, 10, 0, 0)); // renderer artifact: a junction point
  return root;
}

describe('intersects', () => {
  const rect = { x: 0, y: 0, width: 100, height: 100 };
  it('counts touching as visible and separated as not', () => {
    expect(intersects({ x: 100, y: 0, width: 10, height: 10 }, rect)).toBe(true);
    expect(intersects({ x: -10, y: -10, width: 10, height: 10 }, rect)).toBe(true);
    expect(intersects({ x: 101, y: 0, width: 10, height: 10 }, rect)).toBe(false);
    expect(intersects({ x: 0, y: 200, width: 10, height: 10 }, rect)).toBe(false);
    expect(intersects({ x: 10, y: 10, width: 10, height: 10 }, rect)).toBe(true);
  });
  it('viewportRect divides the canvas by the zoom', () => {
    expect(viewportRect({ x: 5, y: 6 }, 2, { width: 200, height: 100 })).toEqual({
      x: 5,
      y: 6,
      width: 100,
      height: 50,
    });
  });
});

describe('modelIds', () => {
  it('lists the sent nodes, ports, labels and edges, not the root or slack artifacts', () => {
    expect([...modelIds(LAYOUT)]).toEqual(['n1', 'l1', 'far', 'n2', 'e1']); // transform order
  });
});

describe('viewedIds', () => {
  const ids = modelIds(LAYOUT);
  it('lists the model elements touching the viewport, in model order', () => {
    const rect = viewportRect({ x: 0, y: 0 }, 1, { width: 200, height: 100 });
    expect(viewedIds(model(), rect, ids)).toEqual(['n1', 'n2']);
  });
  it('never lists a hidden element (its slack port), an edge, a junction or the root', () => {
    const rect = viewportRect({ x: -10, y: -10 }, 0.01, { width: 200, height: 100 });
    const viewed = viewedIds(model(), rect, ids);
    expect(viewed).toEqual(['n1', 'far', 'n2']);
    expect(viewed).not.toContain('hidden');
    expect(viewed).not.toContain('e1_j0');
  });
  it('excludes an off-screen node and includes one the camera just reaches', () => {
    const rect = viewportRect({ x: 900, y: 900 }, 1, { width: 100, height: 100 });
    expect(viewedIds(model(), rect, ids)).toEqual(['far']); // touches at (1000, 1000)
    const rect2 = viewportRect({ x: 899, y: 899 }, 1, { width: 100, height: 100 });
    expect(viewedIds(model(), rect2, ids)).toEqual([]);
  });
});

function report(overrides: Partial<IViewportReport> = {}): IViewportReport {
  return {
    view_id: 'view-a',
    origin: [10, 20],
    zoom: 1.5,
    canvas_size: [640, 480],
    viewed_ids: ['n1', 'n2'],
    ...overrides,
  };
}

describe('sameReport', () => {
  it('ignores float noise and viewed_ids order, not real changes', () => {
    expect(sameReport(report(), report({ origin: [10 + 1e-12, 20] }))).toBe(true);
    expect(sameReport(report(), report({ viewed_ids: ['n2', 'n1'] }))).toBe(true);
    expect(sameReport(report(), report({ zoom: 1.6 }))).toBe(false);
    expect(sameReport(report(), report({ viewed_ids: ['n1'] }))).toBe(false);
    expect(sameReport(report(), report({ view_id: 'view-b' }))).toBe(false);
  });
});

describe('ViewportReporter', () => {
  it('writes two identical reports once', async () => {
    const writes: IViewportReport[] = [];
    const reporter = new ViewportReporter(
      async () => report(),
      (r) => writes.push(r),
    );
    expect(await reporter.report()).toBe(true);
    expect(await reporter.report()).toBe(false);
    expect(writes).toHaveLength(1);
  });

  it('drops a gather superseded by a newer one', async () => {
    const writes: IViewportReport[] = [];
    const pending: Array<(r: IViewportReport) => void> = [];
    const reporter = new ViewportReporter(
      () => new Promise<IViewportReport>((resolve) => pending.push(resolve)),
      (r) => writes.push(r),
    );
    const first = reporter.report();
    const second = reporter.report();
    pending[1](report({ zoom: 2 })); // the newer gather lands first
    pending[0](report({ zoom: 1 })); // the stale one lands after
    expect(await Promise.all([first, second])).toEqual([false, true]);
    expect(writes.map((r) => r.zoom)).toEqual([2]);
  });

  it('re-reports after a relayout that only moved elements under a fixed camera', async () => {
    const writes: IViewportReport[] = [];
    let ids = ['n1', 'n2'];
    const reporter = new ViewportReporter(
      async () => report({ viewed_ids: ids }),
      (r) => writes.push(r),
    );
    await reporter.report();
    ids = ['n1']; // n2 moved off-screen: same origin/zoom/canvas
    expect(await reporter.report()).toBe(true);
    expect(writes.map((r) => r.viewed_ids)).toEqual([['n1', 'n2'], ['n1']]);
  });
});
