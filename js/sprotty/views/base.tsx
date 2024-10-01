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

export function validCanvasBounds(bounds: Bounds): boolean {
  return bounds.width == 0 && bounds.height == 0;
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
    if (!validCanvasBounds(canvasBounds)) {
      // only hide if the canvas's size is set
      return true;
    }

    const ab = getAbsoluteBounds(model);
    return (
      ab.x <= canvasBounds.width &&
      ab.x + ab.width >= 0 &&
      ab.y <= canvasBounds.height &&
      ab.y + ab.height >= 0
    );
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
