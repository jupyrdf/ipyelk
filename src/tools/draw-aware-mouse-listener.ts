import { Action, MouseListener, SModelElement, HoverFeedbackAction } from 'sprotty/lib';
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

  mouseDown(target: SModelElement, event: MouseEvent): Action[] {
    this.isMouseDown = true;
    return [];
  }

  mouseMove(target: SModelElement, event: MouseEvent): Action[] {
    if (this.isMouseDown) {
      this.isMouseDrag = true;
    }
    return [];
  }

  mouseUp(element: SModelElement, event: MouseEvent): Action[] {
    this.isMouseDown = false;
    if (this.isMouseDrag) {
      this.isMouseDrag = false;
      return this.draggingMouseUp(element, event);
    }

    return this.nonDraggingMouseUp(element, event);
  }

  nonDraggingMouseUp(element: SModelElement, event: MouseEvent): Action[] {
    return [];
  }

  draggingMouseUp(element: SModelElement, event: MouseEvent): Action[] {
    return [];
  }
}

export class DragAwareHoverMouseListener extends DragAwareMouseListener {
  constructor(protected elementTypeId: string, protected tool: DiagramTool) {
    super();
  }

  mouseOver(target: SModelElement, event: MouseEvent): Action[] {
    return [new HoverFeedbackAction(target.id, true)];
  }

  mouseOut(target: SModelElement, event: MouseEvent): (Action | Promise<Action>)[] {
    return [new HoverFeedbackAction(target.id, false)];
  }
}
