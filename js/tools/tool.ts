/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { injectable } from 'inversify';

import { Action, MouseListener, Tool } from 'sprotty/lib';

export const TOOL_ID_PREFIX = 'tool';

export function deriveToolId(operationKind: string, elementTypeId?: string) {
  return `${TOOL_ID_PREFIX}_${operationKind}_${elementTypeId}`;
}

export interface IMouseTool {
  register(mouseListener: MouseListener): void;
  deregister(mouseListener: MouseListener): void;
}

// TODO make this an interface?
@injectable()
export class DiagramTool implements Tool {
  public elementTypeId: string = 'unknown';
  public operationKind: string = 'generic';

  get id() {
    return deriveToolId(this.operationKind, this.elementTypeId);
  }

  enable() {}

  disable() {}

  dispatchFeedback(actions: Action[]) {}
}
