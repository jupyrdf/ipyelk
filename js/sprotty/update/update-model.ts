/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 * FIX BELOW FROM:
 */

/********************************************************************************
 * Copyright (c) 2017-2020 TypeFox and others.
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
import { injectable } from 'inversify';
import {
  Animation,
  CommandExecutionContext,
  CompoundAnimation,
  MatchResult,
  ResolvedElementFade,
  SChildElementImpl,
  SModelElementImpl,
  SModelRootImpl,
  SParentElementImpl,
  forEachMatch,
  isFadeable,
} from 'sprotty';
import { UpdateAnimationData, UpdateModelCommand } from 'sprotty';
import { Fadeable } from 'sprotty-protocol';

import { containsSome } from './smodel-utils';

@injectable()
export class UpdateModelCommand2 extends UpdateModelCommand {
  protected computeAnimation(
    newRoot: SModelRootImpl,
    matchResult: MatchResult,
    context: CommandExecutionContext,
  ): SModelRootImpl | Animation {
    const animationData: UpdateAnimationData = {
      fades: [] as ResolvedElementFade[],
    };
    forEachMatch(matchResult, (id, match) => {
      if (match.left !== undefined && match.right !== undefined) {
        // The element is still there, but may have been moved
        this.updateElement(
          match.left as SModelElementImpl,
          match.right as SModelElementImpl,
          animationData,
        );
      } else if (match.right !== undefined) {
        // An element has been added
        const right = match.right as SModelElementImpl;
        if (isFadeable(right)) {
          right.opacity = 0;
          animationData.fades.push({
            element: right,
            type: 'in',
          });
        }
      } else if (match.left instanceof SChildElementImpl) {
        // An element has been removed
        const left = match.left;
        if (isFadeable(left) && match.leftParentId !== undefined) {
          if (!containsSome(newRoot, left)) {
            const parent = newRoot.index.getById(match.leftParentId);
            if (parent instanceof SParentElementImpl) {
              const leftCopy = context.modelFactory.createElement(
                left,
              ) as SChildElementImpl & Fadeable;
              parent.add(leftCopy);
              animationData.fades.push({
                element: leftCopy,
                type: 'out',
              });
            }
          }
        }
      }
    });

    const animations = this.createAnimations(animationData, newRoot, context);
    if (animations.length >= 2) {
      return new CompoundAnimation(newRoot, context, animations);
    } else if (animations.length === 1) {
      return animations[0];
    } else {
      return newRoot;
    }
  }
}
