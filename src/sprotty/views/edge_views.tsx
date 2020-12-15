/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
/*******************************************************************************
 * Copyright (c) 2017 TypeFox GmbH (http://www.typefox.io) and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *******************************************************************************/
import * as snabbdom from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { VNode } from 'snabbdom/vnode';
import {
  // RenderingContext,
  SEdge,
  PolylineEdgeView,
  CircularNodeView,
  Point,
  toDegrees,
  setClass,
  angleOfPoint
} from 'sprotty';
import { ElkJunction, ElkModelRenderer } from '../sprotty-model';

const JSX = { createElement: snabbdom.svg };

class SElkEdge extends SEdge {
  start?: string;
  end?: string;
}

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
  render(edge: Readonly<SEdge>, context: ElkModelRenderer): VNode | undefined {
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
    edge: SElkEdge,
    segments: Point[],
    context: ElkModelRenderer
  ): VNode {
    const p1_s = segments[1];
    const p2_s = segments[0];
    let r = angleOfPoint({ x: p1_s.x - p2_s.x, y: p1_s.y - p2_s.y });

    const p1_e = segments[segments.length - 2];
    const p2_e = segments[segments.length - 1];
    let r2 = angleOfPoint({ x: p1_e.x - p2_e.x, y: p1_e.y - p2_e.y });

    let start = this.getPathOffset(edge.start, context, r);
    let end = this.getPathOffset(edge.end, context, r2);

    const firstPoint = segments[0];
    let path = `M ${firstPoint.x - start.x},${firstPoint.y - start.y}`;
    for (let i = 1; i < segments.length - 1; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    const lastPoint = segments[segments.length - 1];
    path += ` L ${lastPoint.x - end.x}, ${lastPoint.y - end.y}`;
    return <path d={path} />;
  }

  protected getAnchorCorrection(
    id: string | undefined,
    context: ElkModelRenderer,
    r: number
  ): Point {
    let connection = context.getConnector(id);
    if (connection?.correction) {
      const p = connection.correction;
      return {
        x: p.x * Math.cos(r) - p.y * Math.sin(r),
        y: p.x * Math.sin(r) + p.y * Math.cos(r)
      };
    }
    return { x: 0, y: 0 };
  }

  protected getPathOffset(
    id: string | undefined,
    context: ElkModelRenderer,
    r: number
  ): Point {
    let connection = context.getConnector(id);
    if (connection?.offset) {
      const p = connection.offset;
      return {
        x: p.x * Math.cos(r) - p.y * Math.sin(r),
        y: p.x * Math.sin(r) + p.y * Math.cos(r)
      };
    }

    return { x: 0, y: 0 };
  }

  protected renderAdditionals(
    edge: SElkEdge,
    segments: Point[],
    context: ElkModelRenderer
  ): VNode[] {
    let connectors: VNode[] = [];
    let href: string;
    let correction: Point;
    let vnode: VNode;
    if (edge.start) {
      const p1 = segments[1];
      const p2 = segments[0];
      let r = angleOfPoint({ x: p1.x - p2.x, y: p1.y - p2.y });
      correction = this.getAnchorCorrection(edge.start, context, r);

      let x = p2.x - correction.x;
      let y = p2.y - correction.y;
      href = context.hrefID(edge.start);
      vnode = (
        <use
          href={'#' + href}
          class-elkedge-start={true}
          class-elkarrow={true}
          transform={`rotate(${toDegrees(r)} ${x} ${y}) translate(${x} ${y})`}
        />
      );
      setClass(vnode, edge.start, true);
      connectors.push(vnode);
    }
    if (edge.end) {
      const p1 = segments[segments.length - 2];
      const p2 = segments[segments.length - 1];
      let r = angleOfPoint({ x: p1.x - p2.x, y: p1.y - p2.y });
      correction = this.getAnchorCorrection(edge.end, context, r);

      let x = p2.x - correction.x;
      let y = p2.y - correction.y;
      href = context.hrefID(edge.end);
      vnode = (
        <use
          href={'#' + href}
          class-elkedge-end={true}
          class-elkarrow={true}
          transform={`rotate(${toDegrees(r)} ${x} ${y}) translate(${x} ${y})`}
        />
      );
      setClass(vnode, edge.end, true);
      connectors.push(vnode);
    }
    return connectors;
  }
}

export function angle(x0: Point, x1: Point): number {
  return toDegrees(Math.atan2(x1.y - x0.y, x1.x - x0.x));
}
