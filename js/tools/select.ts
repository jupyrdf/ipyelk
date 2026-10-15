/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
//inspired from :
// https://github.com/eclipsesource/graphical-lsp/blob/abc742641f6fc993f708f0c8cef937eb7a0b028a/client/packages/sprotty-client/src/features/tools/creation-tool.ts
import { VNode } from 'snabbdom';

import { inject, injectable } from 'inversify';

import { Action, SelectAction } from 'sprotty-protocol';

import {
  MouseTool,
  SModelElementImpl,
  SRoutingHandleImpl,
  findParentByFeature,
  isCtrlOrCmd,
  isSelectable,
  setClass,
} from 'sprotty';
import { toArray } from 'sprotty/lib/utils/iterable';

import { DragAwareHoverMouseListener } from './draw-aware-mouse-listener';
import { IFeedbackActionDispatcher } from './feedback/feedback-action-dispatcher';
import { DiagramTool, IMouseTool } from './tool';
import { ToolTYPES } from './types';
import { idGetter } from './util';

@injectable()
export class NodeSelectTool extends DiagramTool {
  public elementTypeId: string = 'unknown';
  public operationKind: string = SelectAction.KIND;
  protected selectionToolMouseListener: NodeSelectToolMouseListener;

  constructor(
    @inject(MouseTool) protected mouseTool: IMouseTool,
    @inject(ToolTYPES.IFeedbackActionDispatcher)
    protected feedbackDispatcher: IFeedbackActionDispatcher,
  ) {
    super();
  }

  enable() {
    this.selectionToolMouseListener = new NodeSelectToolMouseListener(
      this.elementTypeId,
      this,
    );
    this.mouseTool.register(this.selectionToolMouseListener);
  }

  disable() {
    this.mouseTool.deregister(this.selectionToolMouseListener);
  }
}

@injectable()
export class NodeSelectToolMouseListener extends DragAwareHoverMouseListener {
  constructor(
    protected elementTypeId: string,
    protected tool: NodeSelectTool,
  ) {
    super(elementTypeId, tool);
  }

  nonDraggingMouseUp(target: SModelElementImpl, event: MouseEvent): Action[] {
    let entering: SModelElementImpl[] = []; // elements entering selection
    let exiting: SModelElementImpl[] = []; // element exiting selection
    if (event.button === 0 && !isJLWidget(event)) {
      const selectableTarget = findParentByFeature(target, isSelectable);
      if (selectableTarget != null) {
        // multi-selection?
        if (!isCtrlOrCmd(event)) {
          exiting = toArray(
            target.root.index
              .all()
              .filter(
                (element) =>
                  isSelectable(element) &&
                  element.selected &&
                  !(
                    selectableTarget instanceof SRoutingHandleImpl &&
                    element === (selectableTarget.parent as SModelElementImpl)
                  ),
              ),
          );
        }
        if (selectableTarget != null) {
          if (!selectableTarget.selected) {
            entering = [selectableTarget];
          } else if (isCtrlOrCmd(event)) {
            exiting = [selectableTarget];
          }
        }
      }
    }

    return [
      SelectAction.create({
        selectedElementsIDs: entering.map(idGetter),
        deselectedElementsIDs: exiting.map(idGetter),
      }),
    ];
  }

  /**
   * Apply CSS `selected` class for selected elements
   * @param vnode
   * @param element
   */
  decorate(vnode: VNode, element: SModelElementImpl): VNode {
    const selectableTarget = findParentByFeature(element, isSelectable);
    if (selectableTarget != null)
      setClass(vnode, 'selected', selectableTarget.selected);
    return vnode;
  }
}

/**
 * Whether a mouse event on a diagram started in a JupyterLab widget that the
 * diagram shows in an overlay (a widget node or the control overlay), on the
 * widget or on any element inside it, such as the icon of a button.
 *
 * The widget must be inside the diagram that handles the event
 * (`currentTarget`): a diagram shown as a widget node of another diagram is
 * itself inside an overlay container, and still selects its own nodes.
 */
export function isJLWidget(event: Pick<Event, 'target' | 'currentTarget'>): boolean {
  const widget = (event.target as Element | null)?.closest?.(
    '.elkcontainer .jupyter-widgets',
  );
  if (widget == null) {
    return false;
  }
  const root = event.currentTarget as Node | null;
  return root == null || root.contains(widget);
}
