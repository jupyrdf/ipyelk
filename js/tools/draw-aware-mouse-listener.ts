/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { MouseListener, SModelElementImpl } from 'sprotty';
import { Action, HoverFeedbackAction } from 'sprotty-protocol';

import { DiagramTool } from './tool';

/**
 * A mouse listener that is aware of prior mouse dragging.
 *
 * Therefore, this listener distinguishes between mouse up events after dragging and
 * mouse up events without prior dragging. Subclasses may override the methods
 * `draggingMouseUp` and/or `nonDraggingMouseUp` to react to only these specific kinds
 * of mouse up events.
 */
export class DragAwareMouseListener extends MouseListener {
  private isMouseDown: boolean = false;
  private isMouseDrag: boolean = false;

  mouseDown(target: SModelElementImpl, event: MouseEvent): Action[] {
    this.isMouseDown = true;
    return [];
  }

  mouseMove(target: SModelElementImpl, event: MouseEvent): Action[] {
    if (this.isMouseDown) {
      this.isMouseDrag = true;
    }
    return [];
  }

  mouseUp(element: SModelElementImpl, event: MouseEvent): Action[] {
    this.isMouseDown = false;
    if (this.isMouseDrag) {
      this.isMouseDrag = false;
      return this.draggingMouseUp(element, event);
    }

    return this.nonDraggingMouseUp(element, event);
  }

  nonDraggingMouseUp(element: SModelElementImpl, event: MouseEvent): Action[] {
    return [];
  }

  draggingMouseUp(element: SModelElementImpl, event: MouseEvent): Action[] {
    return [];
  }
}

export class DragAwareHoverMouseListener extends DragAwareMouseListener {
  constructor(
    protected elementTypeId: string,
    protected tool: DiagramTool,
  ) {
    super();
  }

  mouseOver(target: SModelElementImpl, event: MouseEvent): Action[] {
    return [
      HoverFeedbackAction.create({ mouseoverElement: target.id, mouseIsOver: true }),
    ];
  }

  mouseOut(target: SModelElementImpl, event: MouseEvent): (Action | Promise<Action>)[] {
    return [
      HoverFeedbackAction.create({ mouseoverElement: target.id, mouseIsOver: false }),
    ];
  }
}
