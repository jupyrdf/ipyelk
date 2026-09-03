/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */

/*******************************************************************************
 * Copyright (c) 2017 TypeFox GmbH (http://www.typefox.io) and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *******************************************************************************/

/** @jsx svg */
import { VNode } from 'snabbdom';

import { injectable } from 'inversify';

import { Point, toDegrees } from 'sprotty-protocol';

import {
  PolylineEdgeView,
  SRoutableElementImpl,
  getAbsoluteRouteBounds,
  setClass,
  svg,
} from 'sprotty';

import { ElkModelRenderer } from '../renderer';
import { ElkEdge, ElkJunction } from '../sprotty-model';

import { CircularNodeView, validCanvasBounds } from './base';
import { coveredRoutePoints, routeEndAngle, symbolReach } from './edge_views_util';

@injectable()
export class JunctionView extends CircularNodeView {
  render(node: ElkJunction, context: ElkModelRenderer): VNode {
    const radius = this.getRadius(node);
    return (
      <g>
        <circle class-elkjunction={true} r={radius}></circle>
      </g>
    );
  }

  protected getRadius(node: ElkJunction): number {
    return 2;
  }
}

@injectable()
export class ElkEdgeView extends PolylineEdgeView {
  isVisible(
    model: Readonly<SRoutableElementImpl>,
    route: Point[],
    context: ElkModelRenderer,
  ): boolean {
    if (context.targetKind === 'hidden') {
      // Don't hide any element for hidden rendering
      return true;
    }
    if (route.length === 0) {
      // We should hide only if we know the element's route
      return true;
    }

    const canvasBounds = model.root.canvasBounds;
    if (!validCanvasBounds(canvasBounds)) {
      // only hide if the canvas's size is set
      return true;
    }
    const ab = getAbsoluteRouteBounds(model, route);
    return (
      ab.x <= canvasBounds.width &&
      ab.x + ab.width >= 0 &&
      ab.y <= canvasBounds.height &&
      ab.y + ab.height >= 0
    );
  }

  render(edge: Readonly<ElkEdge>, context: ElkModelRenderer): VNode | undefined {
    const router = this.edgeRouterRegistry.get(edge.routerKind);
    const route = router.route(edge);
    if (route.length === 0) {
      return this.renderDanglingEdge('Cannot compute route', edge, context);
    }
    if (!this.isVisible(edge, route, context)) {
      if (edge.children.length === 0) {
        return undefined;
      }
      // The children of an edge are not necessarily inside the bounding box of the route,
      // so we need to render a group to ensure the children have a chance to be rendered.
      return <g>{context.renderChildren(edge, { route })}</g>;
    }

    return (
      <g class-elkedge={true} class-mouseover={edge.hoverFeedback}>
        {this.renderLine(edge, route, context)}
        {this.renderAdditionals(edge, route, context)}
        {context.renderChildren(edge, { route })}
      </g>
    );
  }

  protected renderLine(
    edge: ElkEdge,
    segments: Point[],
    context: ElkModelRenderer,
  ): VNode {
    const startId = edge?.properties?.shape?.start;
    const endId = edge?.properties?.shape?.end;
    const startReach = symbolReach(context.getConnector(startId));
    const endReach = symbolReach(context.getConnector(endId));
    let r = routeEndAngle(segments, 'source', startReach);
    let r2 = routeEndAngle(segments, 'target', endReach);

    let start = this.getPathOffset(startId, context, r);
    let end = this.getPathOffset(endId, context, r2);

    // interior points beneath an end symbol would make the trimmed shaft
    // double back under it -- skip them
    const first = 1 + coveredRoutePoints(segments, 'source', startReach);
    const last = segments.length - 2 - coveredRoutePoints(segments, 'target', endReach);

    const firstPoint = segments[0];
    let path = `M ${firstPoint.x - start.x},${firstPoint.y - start.y}`;
    for (let i = first; i <= last; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    const lastPoint = segments[segments.length - 1];
    path += ` L ${lastPoint.x - end.x}, ${lastPoint.y - end.y}`;
    return <path d={path} />;
  }

  protected getAnchorOffset(
    id: string | undefined,
    context: ElkModelRenderer,
    r: number,
  ): Point {
    let connection = context.getConnector(id);
    if (connection?.symbol_offset) {
      const p = connection.symbol_offset;
      return {
        x: p.x * Math.cos(r) - p.y * Math.sin(r),
        y: p.x * Math.sin(r) + p.y * Math.cos(r),
      };
    }
    return { x: 0, y: 0 };
  }

  protected getPathOffset(
    id: string | undefined,
    context: ElkModelRenderer,
    r: number,
  ): Point {
    let connection = context.getConnector(id);
    if (connection?.path_offset) {
      const p = connection.path_offset;
      return {
        x: p.x * Math.cos(r) - p.y * Math.sin(r),
        y: p.x * Math.sin(r) + p.y * Math.cos(r),
      };
    }

    return { x: 0, y: 0 };
  }

  protected renderAdditionals(
    edge: ElkEdge,
    segments: Point[],
    context: ElkModelRenderer,
  ): VNode[] {
    let connectors: VNode[] = [];
    let href: string;
    let correction: Point;
    let vnode: VNode;
    let start = edge?.properties?.shape?.start;
    let end = edge?.properties?.shape?.end;
    if (start) {
      const p2 = segments[0];
      let r = routeEndAngle(
        segments,
        'source',
        symbolReach(context.getConnector(start)),
      );

      correction = this.getAnchorOffset(start, context, r);

      let x = p2.x - correction.x;
      let y = p2.y - correction.y;
      href = context.hrefID(start);
      vnode = (
        <use
          href={'#' + href}
          class-elkedge-start={true}
          class-elkarrow={true}
          transform={`rotate(${toDegrees(r)} ${x} ${y}) translate(${x} ${y})`}
        />
      );
      setClass(vnode, start, true);
      connectors.push(vnode);
    }
    if (end) {
      const p2 = segments[segments.length - 1];
      let r = routeEndAngle(segments, 'target', symbolReach(context.getConnector(end)));
      correction = this.getAnchorOffset(end, context, r);

      let x = p2.x - correction.x;
      let y = p2.y - correction.y;
      href = context.hrefID(end);
      vnode = (
        <use
          href={'#' + href}
          class-elkedge-end={true}
          class-elkarrow={true}
          transform={`rotate(${toDegrees(r)} ${x} ${y}) translate(${x} ${y})`}
        />
      );
      setClass(vnode, end, true);
      connectors.push(vnode);
    }
    return connectors;
  }
}

export function angle(x0: Point, x1: Point): number {
  return toDegrees(Math.atan2(x1.y - x0.y, x1.x - x0.x));
}
