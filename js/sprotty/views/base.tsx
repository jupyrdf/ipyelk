/** @jsx svg */
import { VNode } from 'snabbdom';

import { injectable } from 'inversify';

import { Bounds, Dimension, Hoverable, Selectable } from 'sprotty-protocol';

import {
  IView,
  IViewArgs,
  InternalBoundsAware,
  SChildElementImpl,
  SNodeImpl,
  SPortImpl,
  SShapeElementImpl,
  getAbsoluteBounds,
  svg,
} from 'sprotty';

import { ElkModelRenderer } from '../renderer';

/**
 * Whether viewport culling runs at all.
 *
 * Off: a diagram is fit to its canvas when it is laid out, so culling drops
 * nothing on the usual path while costing an absolute-bounds walk per element,
 * and it makes everything that reads the rendered SVG -- the exporter, the
 * acceptance suites, anything scripting the DOM -- depend on where the diagram
 * happens to be scrolled. Turning it back on is #170, which owns the cost
 * measurement and the export path that a partial DOM needs.
 */
export const CULLING_ENABLED: boolean = false;

/**
 * Whether the canvas has a known, non-empty size.
 *
 * Culling compares an element against these bounds: before the first
 * `InitializeCanvasBoundsAction` the root's `canvasBounds` is 0x0 and every
 * element would look off-screen.
 */
export function validCanvasBounds(bounds: Bounds): boolean {
  return bounds.width > 0 && bounds.height > 0;
}

/**
 * Whether elements outside the given canvas may be skipped: only when culling
 * is on at all, and only once the canvas size is known.
 */
export function shouldCull(canvasBounds: Bounds): boolean {
  return CULLING_ENABLED && validCanvasBounds(canvasBounds);
}

/** Whether `bounds` overlaps a canvas of the given size at the origin. */
export function intersectsCanvas(bounds: Bounds, canvasBounds: Bounds): boolean {
  return (
    bounds.x <= canvasBounds.width &&
    bounds.x + bounds.width >= 0 &&
    bounds.y <= canvasBounds.height &&
    bounds.y + bounds.height >= 0
  );
}

@injectable()
export abstract class ShapeView implements IView {
  /**
   * Check whether the given model element is in the current viewport. Use this method
   * in your `render` implementation to skip rendering in case the element is not visible.
   * This can greatly enhance performance for large models.
   */
  isVisible(
    model: Readonly<SChildElementImpl & InternalBoundsAware>,
    context: ElkModelRenderer,
  ): boolean {
    if (context.targetKind === 'hidden') {
      // Don't hide any element for hidden rendering
      return true;
    }
    if (!Dimension.isValid(model.bounds)) {
      // We should hide only if we know the element's bounds
      return true;
    }

    const canvasBounds = model.root.canvasBounds;
    if (!shouldCull(canvasBounds)) {
      return true;
    }

    return intersectsCanvas(getAbsoluteBounds(model), canvasBounds);
  }

  abstract render(
    model: Readonly<SChildElementImpl>,
    context: ElkModelRenderer,
    args?: IViewArgs,
  ): VNode | undefined;
}

@injectable()
export class CircularNodeView extends ShapeView {
  render(
    node: Readonly<SShapeElementImpl & Hoverable & Selectable>,
    context: ElkModelRenderer,
    args?: IViewArgs,
  ): VNode | undefined {
    if (!this.isVisible(node, context)) {
      return undefined;
    }
    const radius = this.getRadius(node);
    return (
      <g>
        <circle
          class-sprotty-node={node instanceof SNodeImpl}
          class-sprotty-port={node instanceof SPortImpl}
          class-mouseover={node.hoverFeedback}
          class-selected={node.selected}
          r={radius}
          cx={radius}
          cy={radius}
        ></circle>
        {context.renderChildren(node)}
      </g>
    );
  }

  protected getRadius(node: SShapeElementImpl): number {
    const d = Math.min(node.size.width, node.size.height);
    return d > 0 ? d / 2 : 0;
  }
}

@injectable()
export class RectangularNodeView extends ShapeView {
  render(
    node: Readonly<SShapeElementImpl & Hoverable & Selectable>,
    context: ElkModelRenderer,
    args?: IViewArgs,
  ): VNode | undefined {
    if (!this.isVisible(node, context)) {
      return undefined;
    }
    return (
      <g>
        <rect
          class-sprotty-node={node instanceof SNodeImpl}
          class-sprotty-port={node instanceof SPortImpl}
          class-mouseover={node.hoverFeedback}
          class-selected={node.selected}
          x="0"
          y="0"
          width={Math.max(node.size.width, 0)}
          height={Math.max(node.size.height, 0)}
        ></rect>
        {context.renderChildren(node)}
      </g>
    );
  }
}
