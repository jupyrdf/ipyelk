/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { Bounds, Dimension, Point, almostEquals } from 'sprotty-protocol';

import {
  SModelRootImpl,
  SRoutableElementImpl,
  getAbsoluteBounds,
  isBoundsAware,
} from 'sprotty';

import { ElkGraphElement, ElkNode } from './sprotty/json/elkgraph-json';

/** What one view writes to the kernel's `Viewer.viewport` in one message. */
export interface IViewportReport {
  view_id: string;
  origin: [number, number];
  zoom: number;
  canvas_size: [number, number];
  viewed_ids: string[];
}

/**
 * Classes assigned by the kernel's `VisIndex` to synthetic ports and edges for
 * hidden elements. A slack port carries the hidden element's id, so it does not
 * itself make that element visible.
 */
export const SLACK_CLASSES = ['slack-port', 'slack-edge'];

function isSlack(element: ElkGraphElement): boolean {
  const classes = (element.properties?.cssClasses || '').split(' ');
  return SLACK_CLASSES.some((cls) => classes.includes(cls));
}

/** An element and its (nested) labels, as the ELK -> sprotty transform walks them. */
function* walkLabelled(element: ElkGraphElement): Generator<ElkGraphElement> {
  yield element;
  for (const label of element.labels || []) {
    yield* walkLabelled(label);
  }
}

/** Node subtree in the ELK -> sprotty transform's order: children, ports, labels, edges. */
function* walkModel(node: ElkNode): Generator<ElkGraphElement> {
  yield node;
  for (const child of node.children || []) {
    yield* walkModel(child);
  }
  for (const port of node.ports || []) {
    yield* walkLabelled(port);
  }
  for (const label of node.labels || []) {
    yield* walkLabelled(label);
  }
  for (const edge of node.edges || []) {
    yield* walkLabelled(edge);
  }
}

/**
 * The ids of the elements the kernel actually sent, root excluded: nodes, ports,
 * labels and edges, minus the slack ports/edges that stand in for hidden elements.
 * Everything else in the sprotty index (junctions, symbols) is a renderer artifact.
 */
export function modelIds(layout: ElkNode): Set<string> {
  const ids = new Set<string>();
  for (const element of walkModel(layout)) {
    if (element !== layout && element.id != null && !isSlack(element)) {
      ids.add(element.id);
    }
  }
  return ids;
}

/** Closed-interval overlap: touching counts. */
export function intersects(a: Bounds, b: Bounds): boolean {
  return (
    a.x <= b.x + b.width &&
    a.x + a.width >= b.x &&
    a.y <= b.y + b.height &&
    a.y + a.height >= b.y
  );
}

/** The diagram-coordinate rectangle a viewport shows. */
export function viewportRect(scroll: Point, zoom: number, canvas: Dimension): Bounds {
  return {
    x: scroll.x,
    y: scroll.y,
    width: canvas.width / zoom,
    height: canvas.height / zoom,
  };
}

/**
 * Ids of the model elements whose absolute bounds touch `rect`, in index (model)
 * order. Edges are never listed: they have no bounds of their own (sprotty derives
 * a hull from the routing points, which is empty for an unrouted edge).
 */
export function viewedIds(
  root: SModelRootImpl,
  rect: Bounds,
  ids: ReadonlySet<string>,
): string[] {
  const viewed: string[] = [];
  for (const element of root.index.all()) {
    if (
      element === root ||
      !ids.has(element.id) ||
      element instanceof SRoutableElementImpl ||
      !isBoundsAware(element)
    ) {
      continue;
    }
    if (intersects(getAbsoluteBounds(element), rect)) {
      viewed.push(element.id);
    }
  }
  return viewed;
}

function sameIds(a: readonly string[], b: readonly string[]): boolean {
  const set = new Set(a);
  return b.every((id) => set.has(id)) && new Set(b).size === set.size;
}

/** Two reports the kernel would not tell apart: skip the second write. */
export function sameReport(a: IViewportReport, b: IViewportReport): boolean {
  return (
    a.view_id === b.view_id &&
    almostEquals(a.origin[0], b.origin[0]) &&
    almostEquals(a.origin[1], b.origin[1]) &&
    almostEquals(a.zoom, b.zoom) &&
    almostEquals(a.canvas_size[0], b.canvas_size[0]) &&
    almostEquals(a.canvas_size[1], b.canvas_size[1]) &&
    sameIds(a.viewed_ids, b.viewed_ids)
  );
}

/**
 * Serializes viewport reports for one view: `report()` gathers a snapshot, drops it
 * when a newer `report()` started meanwhile (the later gather reads the later
 * camera), skips it when it `sameReport`s the last write, and otherwise writes it.
 * Resolves to whether a write happened.
 */
export class ViewportReporter {
  private generation = 0;
  private last: IViewportReport | null = null;

  constructor(
    private readonly gather: () => Promise<IViewportReport | null>,
    private readonly write: (report: IViewportReport) => void,
  ) {}

  async report(): Promise<boolean> {
    const generation = ++this.generation;
    const report = await this.gather();
    if (report == null || generation !== this.generation) {
      return false;
    }
    if (this.last != null && sameReport(this.last, report)) {
      return false;
    }
    this.last = report;
    this.write(report);
    return true;
  }
}
