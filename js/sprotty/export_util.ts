/**
 * Copyright (c) 2025 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { Bounds } from 'sprotty-protocol';

import {
  BoundsAware,
  SChildElementImpl,
  SParentElementImpl,
  isBoundsAware,
} from 'sprotty';

/**
 * An element's bounds in the diagram's own coordinates.
 *
 * This is `getAbsoluteBounds` without its last step: that one also applies the
 * root's `localToParent`, which is the viewport's zoom and scroll, and an
 * export must not move when the diagram is scrolled.
 */
function diagramBounds(element: SChildElementImpl & BoundsAware): Bounds {
  let bounds: Bounds = element.bounds;
  let current: SParentElementImpl = element;
  while (current instanceof SChildElementImpl) {
    const parent = current.parent;
    if (!(parent instanceof SChildElementImpl)) {
      // the root: its transform is the viewport, not part of the diagram
      break;
    }
    bounds = parent.localToParent(bounds);
    current = parent;
  }
  return bounds;
}

/** Depth-first walk over every descendant of `parent`. */
function* descendants(
  parent: Readonly<SParentElementImpl>,
): Generator<SChildElementImpl> {
  for (const child of parent.children) {
    yield child;
    yield* descendants(child);
  }
}

/**
 * The extent of a diagram's content, in diagram coordinates.
 *
 * ELK sizes a graph's children but leaves the graph itself unsized, so an
 * export sizes its viewBox from the model instead. Every descendant counts,
 * not just the root's children: an edge label, a node label placed outside its
 * node, and a port straddling its node's border all draw beyond the bounds of
 * whatever contains them. Measuring the model rather than the DOM keeps the
 * exported size independent of the viewport and of the browser's layout.
 *
 * Returns `Bounds.EMPTY` for a root with nothing to draw.
 */
export function contentBounds(root: Readonly<SParentElementImpl>): Bounds {
  let left = Infinity;
  let top = Infinity;
  let right = -Infinity;
  let bottom = -Infinity;

  for (const element of descendants(root)) {
    if (!isBoundsAware(element)) {
      continue;
    }
    const { x, y, width, height } = diagramBounds(element);
    if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height)) {
      // an edge with no route: its bounds reduce to NaN
      continue;
    }
    left = Math.min(left, x);
    top = Math.min(top, y);
    right = Math.max(right, x + width);
    bottom = Math.max(bottom, y + height);
  }

  if (!isFinite(left)) {
    return Bounds.EMPTY;
  }
  return { x: left, y: top, width: right - left, height: bottom - top };
}

/**
 * The size an exported diagram needs, in diagram coordinates.
 *
 * The export's viewBox starts at the origin, where ELK's layout also starts,
 * so content is measured from there rather than from its own top left corner.
 */
export function contentExtent(root: Readonly<SParentElementImpl>): Bounds {
  const bounds = contentBounds(root);
  return {
    x: 0,
    y: 0,
    width: Math.max(0, bounds.x + bounds.width),
    height: Math.max(0, bounds.y + bounds.height),
  };
}
