/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */

/********************************************************************************
 * Copyright (c) 2019 EclipseSource and others.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0.
 *
 * This Source Code may also be made available under the following Secondary
 * Licenses when the conditions for such availability set forth in the Eclipse
 * Public License v. 2.0 are satisfied: GNU General Public License, version 2
 * with the GNU Classpath Exception which is available at
 * https://www.gnu.org/software/classpath/license.html.
 *
 * SPDX-License-Identifier: EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0
 ********************************************************************************/
import { inject, injectable } from 'inversify';
import {
  Action,
  CommandExecutionContext,
  SModelElement,
  SModelRoot,
  TYPES,
} from 'sprotty/lib';

import { FeedbackCommand } from './model';
import { addCssClasses, removeCssClasses } from './utils';

export enum CursorCSS {
  DEFAULT = 'default-mode',
  OVERLAP_FORBIDDEN = 'overlap-forbidden-mode',
  NODE_CREATION = 'node-creation-mode',
  EDGE_CREATION_SOURCE = 'edge-creation-select-source-mode',
  EDGE_CREATION_TARGET = 'edge-creation-select-target-mode',
  EDGE_RECONNECT = 'edge-reconnect-select-target-mode',
  OPERATION_NOT_ALLOWED = 'edge-modification-not-allowed-mode',
  ELEMENT_DELETION = 'element-deletion-mode',
  MOUSEOVER = 'mouseover',
  SELECTED = 'selected',
}

export class ApplyCSSFeedbackAction implements Action {
  kind = ApplyCursorCSSFeedbackActionCommand.KIND;
  constructor(readonly target?: SModelElement, readonly cssClass?: CursorCSS) {}
}

@injectable()
export class ApplyCursorCSSFeedbackActionCommand extends FeedbackCommand {
  static readonly KIND = 'applyCursorCssFeedback';

  constructor(@inject(TYPES.Action) readonly action: ApplyCSSFeedbackAction) {
    super();
  }
  execute(context: CommandExecutionContext): SModelRoot {
    removeCssClasses(this.action.target, Object.values(CursorCSS));
    if (this.action.cssClass) {
      addCssClasses(this.action.target, [this.action.cssClass]);
    }
    return context.root;
  }
}
