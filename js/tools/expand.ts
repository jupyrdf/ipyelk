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

import { DragAwareMouseListener } from './draw-aware-mouse-listener';
import { IFeedbackActionDispatcher } from './feedback/feedback-action-dispatcher';
import { DiagramTool, IMouseTool } from './tool';
import { ToolTYPES } from './types';
import { idGetter } from './util';

export class ExpandAction implements Action {
  static readonly KIND = 'elementExpand';
  kind = SelectAction.KIND;

  constructor(
    public readonly expandElementsIDs: string[] = [],
    public readonly contractElementsIDs: string[] = [],
  ) {}
}

@injectable()
export class NodeExpandTool extends DiagramTool {
  public elementTypeId: string = 'unknown';
  protected expansionToolMouseListener: NodeExpandToolMouseListener;
  public operationKind: string = ExpandAction.KIND;

  constructor(
    @inject(MouseTool) protected mouseTool: IMouseTool,
    @inject(ToolTYPES.IFeedbackActionDispatcher)
    protected feedbackDispatcher: IFeedbackActionDispatcher,
  ) {
    super();
  }

  enable() {
    this.expansionToolMouseListener = new NodeExpandToolMouseListener(
      this.elementTypeId,
      this,
    );
    this.mouseTool.register(this.expansionToolMouseListener);
  }

  disable() {
    this.mouseTool.deregister(this.expansionToolMouseListener);
  }

  dispatchFeedback(actions: Action[]) {
    this.feedbackDispatcher.registerFeedback(this, actions);
  }
}

@injectable()
export class NodeExpandToolMouseListener extends DragAwareMouseListener {
  constructor(
    protected elementTypeId: string,
    protected tool: NodeExpandTool,
  ) {
    super();
  }

  wheel(target: SModelElementImpl, event: MouseEvent): Action[] {
    return [];
    let entering: SModelElementImpl[] = []; // elements entering selection
    let exiting: SModelElementImpl[] = []; // element exiting selection

    if (event.button === 0) {
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
   *  TODO replace with `this.tool.dispatchFeedback`?
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
