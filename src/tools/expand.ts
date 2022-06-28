/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
//inspired from :
// https://github.com/eclipsesource/graphical-lsp/blob/abc742641f6fc993f708f0c8cef937eb7a0b028a/client/packages/sprotty-client/src/features/tools/creation-tool.ts

import { inject, injectable } from 'inversify';

import { VNode } from 'snabbdom/vnode';

import {
  Action,
  SModelElement,
  MouseTool,
  SelectAction,
  findParentByFeature,
  isCtrlOrCmd,
  isSelectable,
  SModelRoot,
  SRoutingHandle,
  setClass
} from 'sprotty/lib';
import { toArray } from 'sprotty/lib/utils/iterable';

import { ToolTYPES } from './types';
import { IFeedbackActionDispatcher } from './feedback/feedback-action-dispatcher';
import { DragAwareMouseListener } from './draw-aware-mouse-listener';
import { DiagramTool, IMouseTool } from './tool';
import { idGetter } from './util';

export class ExpandAction implements Action {
  static readonly KIND = 'elementExpand';
  kind = SelectAction.KIND;

  constructor(
    public readonly expandElementsIDs: string[] = [],
    public readonly contractElementsIDs: string[] = []
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
    protected feedbackDispatcher: IFeedbackActionDispatcher
  ) {
    super();
  }

  enable() {
    this.expansionToolMouseListener = new NodeExpandToolMouseListener(
      this.elementTypeId,
      this
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
  constructor(protected elementTypeId: string, protected tool: NodeExpandTool) {
    super();
  }

  wheel(target: SModelElement, event: MouseEvent): Action[] {
    return [];
    let entering: SModelElement[] = []; // elements entering selection
    let exiting: SModelElement[] = []; // element exiting selection

    if (event.button === 0) {
      const selectableTarget = findParentByFeature(target, isSelectable);
      if (selectableTarget != null || target instanceof SModelRoot) {
        // multi-selection?
        if (!isCtrlOrCmd(event)) {
          exiting = toArray(
            target.root.index
              .all()
              .filter(
                element =>
                  isSelectable(element) &&
                  element.selected &&
                  !(
                    selectableTarget instanceof SRoutingHandle &&
                    element === (selectableTarget.parent as SModelElement)
                  )
              )
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

    return [new SelectAction(entering.map(idGetter), exiting.map(idGetter))];
  }

  /**
   * Apply CSS `selected` class for selected elements
   *  TODO replace with `this.tool.dispatchFeedback`?
   * @param vnode
   * @param element
   */
  decorate(vnode: VNode, element: SModelElement): VNode {
    const selectableTarget = findParentByFeature(element, isSelectable);
    if (selectableTarget != null)
      setClass(vnode, 'selected', selectableTarget.selected);
    return vnode;
  }
}
