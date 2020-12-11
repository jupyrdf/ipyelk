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
  RenderingContext,
  SEdge,
  PolylineEdgeView,
  CircularNodeView,
  Point,
  toDegrees,
  angleOfPoint,
  getSubType
} from 'sprotty';
import { ElkJunction } from '../sprotty-model';

const JSX = { createElement: snabbdom.svg };

class SElkEdge extends SEdge {
  start?: string;
  end?: string;
}

@injectable()
export class JunctionView extends CircularNodeView {
  render(node: ElkJunction, context: RenderingContext): VNode {
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
  protected renderLine(
    edge: SElkEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode {
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    console.log('ElkEdge subtype-2', getSubType(edge));
    return <path class-elkedge={true} d={path} />;
  }

  protected renderAdditionals(
    edge: SElkEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {

    console.warn("render additionals", edge, segments, context);

    let connectors:VNode[] = [];
    let href: string;
    if (edge.start){
      console.log("angle", angleOfPoint)
      const p1 = segments[1];
      const p2 = segments[0];
      href = `#${edge.start}`
      connectors.push(
      <use
        href={href}
        class-edge={true}
        class-arrow={true}
        transform={`rotate(${toDegrees(
          angleOfPoint({ x: p1.x - p2.x, y: p1.y - p2.y })
        )} ${p2.x} ${p2.y}) translate(${p2.x} ${p2.y})`}
      />
      );
    };
    if (edge.end){
      href = `#${edge.end}`
      const p1 = segments[segments.length - 2];
      const p2 = segments[segments.length - 1];
      connectors.push(
      <use
        href={href}
        class-edge={true}
        class-arrow={true}
        transform={`rotate(${toDegrees(
          angleOfPoint({ x: p1.x - p2.x, y: p1.y - p2.y })
        )} ${p2.x} ${p2.y}) translate(${p2.x} ${p2.y})`}
      />
      );
    };
    return connectors;
  }
}

@injectable()
export class SpecializationEdgeView extends PolylineEdgeView {
  protected renderLine(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode {
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length - 1; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    const lastPoint = segments[segments.length - 1];
    path += ` L ${lastPoint.x}, ${
      lastPoint.y > firstPoint.y ? lastPoint.y - 10 : lastPoint.y + 10
    }`;
    return <path class-elkedge={true} class-specializes={true} d={path} />;
  }
}

@injectable()
export class RestrictsEdgeView extends PolylineEdgeView {
  protected renderLine(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode {
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length - 1; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    const lastPoint = segments[segments.length - 1];
    path += ` L ${lastPoint.x}, ${lastPoint.y}`;
    return <path class-sprotty-edge={true} class-restriction={true} d={path} />;
  }
}

@injectable()
export class CompositionEdgeView extends ElkEdgeView {
  protected renderAdditionals(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {
    const p1 = segments[0];
    const p2 = segments[1];
    const r = 6;
    const rhombStr = `M 0,0 l${r},${r / 2} l${r},-${r / 2} l-${r},-${r / 2} l-${r},${r /
      2} Z`;
    return [
      <path
        class-elkedge={true}
        class-composition={true}
        d={rhombStr}
        transform={`rotate(${angle(p1, p2)} ${p1.x} ${p1.y}) translate(${p1.x} ${
          p1.y
        })`}
      />
    ];
  }

  static readonly SOURCE_CORRECTION = Math.sqrt(1 * 1 + 2 * 2);

  protected getSourceAnchorCorrection(edge: SEdge): number {
    return CompositionEdgeView.SOURCE_CORRECTION;
  }
}

@injectable()
export class StandardEdgeView extends PolylineEdgeView {
  protected renderLine(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode {
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length - 1; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    const secondLastPoint = segments[segments.length - 2];
    const lastPoint = segments[segments.length - 1];
    const isDownArrow = lastPoint.y > secondLastPoint.y;
    path += ` L ${lastPoint.x}, ${isDownArrow ? lastPoint.y - 10 : lastPoint.y + 10}`;
    return <path class-sprotty-edge={true} d={path} />;
  }
}

@injectable()
export class RelationshipEdgeView extends PolylineEdgeView {
  protected renderLine(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode {
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length - 1; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    const lastPoint = segments[segments.length - 1];
    path += ` L ${lastPoint.x}, ${lastPoint.y}`;
    return <path class-sprotty-edge={true} class-relationship={true} d={path} />;
  }
}

@injectable()
export class ImportEdgeView extends SpecializationEdgeView {
  protected renderAdditionals(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {
    const p1 = segments[segments.length - 2];
    const p2 = segments[segments.length - 1];
    return [
      <path
        class-sprotty-edge={true}
        d="M 10,-4 L 0,0 L 10,4"
        transform={`rotate(${angle(p2, p1)} ${p2.x} ${p2.y}) translate(${p2.x} ${
          p2.y
        })`}
      />
    ];
  }

  static readonly TARGET_CORRECTION = Math.sqrt(1 * 1 + 2.5 * 2.5);

  protected getTargetAnchorCorrection(edge: SEdge): number {
    return ImportEdgeView.TARGET_CORRECTION;
  }
}

@injectable()
export class ArrowEdgeView extends StandardEdgeView {
  protected renderAdditionals(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {
    const p1 = segments[segments.length - 2];
    const p2 = segments[segments.length - 1];
    return [
      <polygon
        class-sprotty-edge={true}
        points="10,-4 0,0 10,4"
        transform={`rotate(${angle(p2, p1)} ${p2.x} ${p2.y}) translate(${p2.x} ${
          p2.y
        })`}
      />
    ];
  }

  static readonly TARGET_CORRECTION = Math.sqrt(1 * 1 + 2.5 * 2.5);

  protected getTargetAnchorCorrection(edge: SEdge): number {
    return ArrowEdgeView.TARGET_CORRECTION;
  }
}

@injectable()
export class RelationshipArrowEdgeView extends RelationshipEdgeView {
  protected renderAdditionals(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {
    const p1 = segments[segments.length - 2];
    const p2 = segments[segments.length - 1];
    return [
      <path
        class-sprotty-edge={true}
        class-relationship={true}
        d="M 10,-4 L 0,0 L 10,4"
        transform={`rotate(${angle(p2, p1)} ${p2.x} ${p2.y}) translate(${p2.x} ${
          p2.y
        })`}
      />
    ];
  }

  static readonly TARGET_CORRECTION = Math.sqrt(1 * 1 + 2.5 * 2.5);

  protected getTargetAnchorCorrection(edge: SEdge): number {
    return ArrowEdgeView.TARGET_CORRECTION;
  }
}

@injectable()
export class RestrictsArrowEdgeView extends RestrictsEdgeView {
  protected renderAdditionals(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {
    const p1 = segments[segments.length - 2];
    const p2 = segments[segments.length - 1];
    return [
      <path
        class-sprotty-edge={true}
        class-restriction={true}
        d="M 10,-4 L 0,0 L 10,4"
        transform={`rotate(${angle(p2, p1)} ${p2.x} ${p2.y}) translate(${p2.x} ${
          p2.y
        })`}
      />
    ];
  }

  static readonly TARGET_CORRECTION = Math.sqrt(1 * 1 + 2.5 * 2.5);

  protected getTargetAnchorCorrection(edge: SEdge): number {
    return ArrowEdgeView.TARGET_CORRECTION;
  }
}

@injectable()
export class SpecializationArrowEdgeView extends SpecializationEdgeView {
  protected renderAdditionals(
    edge: SEdge,
    segments: Point[],
    context: RenderingContext
  ): VNode[] {
    const p1 = segments[segments.length - 2];
    const p2 = segments[segments.length - 1];
    return [
      <polygon
        class-sprotty-edge={true}
        class-specializes={true}
        points="10,-4 0,0 10,4"
        transform={`rotate(${angle(p2, p1)} ${p2.x} ${p2.y}) translate(${p2.x} ${
          p2.y
        })`}
      />
    ];
  }

  static readonly TARGET_CORRECTION = Math.sqrt(1 * 1 + 2.5 * 2.5);

  protected getTargetAnchorCorrection(edge: SEdge): number {
    return SpecializationArrowEdgeView.TARGET_CORRECTION;
  }
}

export function angle(x0: Point, x1: Point): number {
  return toDegrees(Math.atan2(x1.y - x0.y, x1.x - x0.x));
}
