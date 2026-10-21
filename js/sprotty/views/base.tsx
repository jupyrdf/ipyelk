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
 * Whether the canvas has a known, non-empty size.
 *
 * Culling compares an element against these bounds: before the first
 * `InitializeCanvasBoundsAction` the root's `canvasBounds` is 0x0 and every
 * element would look off-screen.
 */
export function validCanvasBounds(bounds: Bounds): boolean {
  return bounds.width > 0 && bounds.height > 0;
}

/** The part of the render context that decides whether culling runs. */
export type CullingContext = Pick<ElkModelRenderer, 'targetKind'> & {
  source?: { culling: boolean };
};

/**
 * Whether elements outside the given canvas may be skipped: only when the
 * view's model source has culling on (see `JLModelSource.culling`), never for
 * the hidden bounds-measuring render, and only once the canvas size is known.
 */
export function shouldCull(context: CullingContext, canvasBounds: Bounds): boolean {
  if (context.targetKind === 'hidden') {
    return false;
  }
  return context.source?.culling === true && validCanvasBounds(canvasBounds);
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
    const canvasBounds = model.root.canvasBounds;
    if (!shouldCull(context, canvasBounds)) {
      return true;
    }
    if (!Dimension.isValid(model.bounds)) {
      // We should hide only if we know the element's bounds
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
