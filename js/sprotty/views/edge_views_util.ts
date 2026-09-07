/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { Point, angleOfPoint } from 'sprotty-protocol';

import { SElkConnectorSymbol } from '../json/symbols';

/**
 * Zero-length route chords make `angleOfPoint` return 0 (atan2(0, 0)):
 * elkjs SPLINES sections duplicate control points at the section knots, so
 * the naive "adjacent segment" tangent flipped end symbols 180 degrees on
 * any right-to-left end (the head rendered pointing INTO the target node).
 * Points closer together than this are never used as a tangent reference.
 */
export const MIN_TANGENT_LENGTH = 1e-3;

/**
 * Angle (radians) of the route at one of its ends, pointing from that end
 * point INTO the edge.
 *
 * Instead of the adjacent route segment -- which may be a zero-length
 * spline chord (see MIN_TANGENT_LENGTH) or a stub shorter than the symbol
 * riding it (elk POLYLINE bends within a few px of the node: a 12px
 * membership diamond then straddles the bend, drawn axis-aligned while the
 * visible shaft leaves diagonally) -- the tangent is the chord from the
 * end point to the route point `reach` px along the route. That is exact
 * on straight and orthogonal ends (the layout keeps bends out of a
 * symbol's footprint there) and the symbol's average direction otherwise.
 */
export function routeEndAngle(
  route: Point[],
  end: 'source' | 'target',
  reach: number,
): number {
  const points = end === 'source' ? route : [...route].reverse();
  const origin = points[0];
  const distance = Math.max(reach, MIN_TANGENT_LENGTH);
  let travelled = 0;
  for (let i = 1; i < points.length; i++) {
    const segment = Point.euclideanDistance(points[i - 1], points[i]);
    if (segment >= MIN_TANGENT_LENGTH && travelled + segment >= distance) {
      const t = Math.min((distance - travelled) / segment, 1);
      const ref = {
        x: points[i - 1].x + (points[i].x - points[i - 1].x) * t,
        y: points[i - 1].y + (points[i].y - points[i - 1].y) * t,
      };
      return angleOfPoint({ x: ref.x - origin.x, y: ref.y - origin.y });
    }
    travelled += segment;
  }
  // route shorter than the reach: fall back to the farthest distinct point
  for (let i = points.length - 1; i > 0; i--) {
    const p = points[i];
    if (Point.euclideanDistance(origin, p) >= MIN_TANGENT_LENGTH) {
      return angleOfPoint({ x: p.x - origin.x, y: p.y - origin.y });
    }
  }
  return 0;
}

/**
 * How far back along the shaft a connector symbol reaches: its
 * `path_offset` pulls the line end from under the symbol body, so its
 * length is exactly the footprint the symbol covers.
 */
export function symbolReach(connection?: SElkConnectorSymbol): number {
  const offset = connection?.path_offset;
  return offset ? Math.sqrt(offset.x * offset.x + offset.y * offset.y) : 0;
}

/**
 * Number of interior route points within `reach` (arc length) of the given
 * route end. The shaft is trimmed by the end symbols' path offsets, so
 * bends this close to an end would make the drawn path double back beneath
 * the symbol (elk polyline stubs, elkjs spline knot duplicates); the
 * renderer drops them from the path.
 */
export function coveredRoutePoints(
  route: Point[],
  end: 'source' | 'target',
  reach: number,
): number {
  const points = end === 'source' ? route : [...route].reverse();
  let travelled = 0;
  let covered = 0;
  for (let i = 1; i < points.length - 1; i++) {
    travelled += Point.euclideanDistance(points[i - 1], points[i]);
    if (travelled >= reach) {
      break;
    }
    covered += 1;
  }
  return covered;
}
