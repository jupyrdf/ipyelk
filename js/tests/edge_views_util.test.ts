/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import { Point, angleOfPoint } from 'sprotty-protocol';

import { coveredRoutePoints, routeEndAngle, symbolReach } from '../sprotty/views/edge_views_util';

/** the tangent the old renderer used: the chord of the adjacent segment */
function naiveEndAngle(route: Point[], end: 'source' | 'target'): number {
  const p1 = end === 'source' ? route[1] : route[route.length - 2];
  const p2 = end === 'source' ? route[0] : route[route.length - 1];
  return angleOfPoint({ x: p1.x - p2.x, y: p1.y - p2.y });
}

describe('routeEndAngle', () => {
  it('is exact on a straight edge', () => {
    const route: Point[] = [
      { x: 0, y: 0 },
      { x: 10, y: 10 },
    ];
    expect(routeEndAngle(route, 'source', 5)).toBeCloseTo(Math.PI / 4);
    expect(routeEndAngle(route, 'target', 5)).toBeCloseTo((-3 * Math.PI) / 4);
  });

  it('ignores the duplicated control points of elkjs SPLINES sections', () => {
    // elkjs SPLINES sections repeat the knot point where sections join, so
    // the terminal chord is zero-length
    const route: Point[] = [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 20, y: 0 },
      { x: 20, y: 0 },
    ];
    // the old adjacent-segment tangent collapsed to atan2(0, 0) = 0: the
    // end symbol rendered 180 degrees wrong, inside the target node
    expect(naiveEndAngle(route, 'target')).toBe(0);
    expect(routeEndAngle(route, 'target', 6)).toBeCloseTo(Math.PI);
  });

  it('reaches past a short POLYLINE exit stub to the visible diagonal', () => {
    // elk POLYLINE leaves the node with a short axis-aligned stub before
    // the first bend; a 12px symbol straddles that bend
    const route: Point[] = [
      { x: 0, y: 0 },
      { x: 2, y: 0 },
      { x: 30, y: 28 },
    ];
    // the old tangent followed the 2px stub, not the shaft under the symbol
    expect(naiveEndAngle(route, 'source')).toBe(0);
    const angle = routeEndAngle(route, 'source', 12);
    expect(angle).toBeGreaterThan(Math.PI / 6);
    expect(angle).toBeLessThan(Math.PI / 4);
  });

  it('falls back to the farthest distinct point on short routes', () => {
    const route: Point[] = [
      { x: 0, y: 0 },
      { x: 3, y: 4 },
    ];
    expect(routeEndAngle(route, 'source', 100)).toBeCloseTo(Math.atan2(4, 3));
  });

  it('returns 0 on a fully degenerate route', () => {
    const route: Point[] = [
      { x: 5, y: 5 },
      { x: 5, y: 5 },
    ];
    expect(routeEndAngle(route, 'source', 10)).toBe(0);
  });
});

describe('symbolReach', () => {
  it('is the length of the connector path offset', () => {
    expect(symbolReach({ path_offset: { x: -6, y: 0 } } as any)).toBe(6);
    expect(symbolReach({ path_offset: { x: 3, y: 4 } } as any)).toBe(5);
  });

  it('is 0 without a connector or offset', () => {
    expect(symbolReach(undefined)).toBe(0);
    expect(symbolReach({} as any)).toBe(0);
  });
});

describe('coveredRoutePoints', () => {
  const route: Point[] = [
    { x: 0, y: 0 },
    { x: 2, y: 0 },
    { x: 30, y: 28 },
    { x: 30, y: 28 },
  ];

  it('drops interior bends under a symbol footprint', () => {
    // the 2px stub bend sits beneath a 12px start symbol
    expect(coveredRoutePoints(route, 'source', 12)).toBe(1);
    // the duplicated end knot sits beneath any end symbol
    expect(coveredRoutePoints(route, 'target', 6)).toBe(1);
  });

  it('keeps bends beyond the symbol footprint', () => {
    expect(coveredRoutePoints(route, 'source', 1)).toBe(0);
    expect(coveredRoutePoints(route, 'source', 0)).toBe(0);
  });

  it('never counts the route end points themselves', () => {
    expect(coveredRoutePoints(route, 'source', 1e6)).toBe(route.length - 2);
  });
});
