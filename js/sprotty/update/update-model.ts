/**
 * Copyright (c) 2024 ipyelk contributors.
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

import { Fadeable } from 'sprotty-protocol';

import {
  Animation,
  CommandExecutionContext,
  CompoundAnimation,
  FadeAnimation,
  MatchResult,
  ResolvedElementFade,
  SChildElementImpl,
  SModelElementImpl,
  SModelRootImpl,
  SParentElementImpl,
  forEachMatch,
  isFadeable,
  isHoverable,
} from 'sprotty';
import { UpdateAnimationData, UpdateModelCommand } from 'sprotty';

import { containsSome } from './smodel-utils';

/**
 * A `FadeAnimation` whose last frame may run twice.
 *
 * Sprotty's removes faded-out elements when the EASED time is 1, but `Animation`
 * only stops when the raw time is 1, and `easeInOut` already rounds to 1 within
 * about 1e-8 of the end: a frame landing a hair before the duration (regular
 * timestamps, e.g. 15 frames of 1000/60 ms for 250 ms) removes them, then
 * the real last frame removes them again and `remove` throws. The throw happens
 * in an animation-frame callback, so the animation never settles, sprotty's
 * command stack waits on it forever, and no later model update is drawn (gh-95).
 */
export class FadeOnceAnimation extends FadeAnimation {
  tween(t: number, context: CommandExecutionContext): SModelRootImpl {
    for (const { element, type } of this.elementFades) {
      if (type === 'in') {
        element.opacity = t;
      } else if (type === 'out') {
        element.opacity = 1 - t;
        if (
          t === 1 &&
          this.removeAfterFadeOut &&
          element instanceof SChildElementImpl &&
          element.parent.children.includes(element)
        ) {
          element.parent.remove(element);
        }
      }
    }
    return this.model;
  }
}

@injectable()
export class UpdateModelCommand2 extends UpdateModelCommand {
  protected createAnimations(
    data: UpdateAnimationData,
    root: SModelRootImpl,
    context: CommandExecutionContext,
  ): Animation[] {
    return super
      .createAnimations(data, root, context)
      .map((animation) =>
        animation instanceof FadeAnimation && !(animation instanceof FadeOnceAnimation)
          ? new FadeOnceAnimation(root, animation.elementFades, context, true)
          : animation,
      );
  }

  protected updateElement(
    left: SModelElementImpl,
    right: SModelElementImpl,
    animationData: UpdateAnimationData,
  ): void {
    super.updateElement(left, right, animationData);
    /**
     * Sprotty preserves `selected` and the camera when replacing an element, but
     * not `hoverFeedback`. Preserve it so a paint, re-layout, or overlay update
     * under a stationary pointer does not discard the hover state.
     */
    if (isHoverable(left) && isHoverable(right)) {
      right.hoverFeedback = left.hoverFeedback;
    }
  }

  protected computeAnimation(
    newRoot: SModelRootImpl,
    matchResult: MatchResult,
    context: CommandExecutionContext,
  ): SModelRootImpl | Animation {
    const animationData: UpdateAnimationData = {
      fades: [] as ResolvedElementFade[],
    };
    forEachMatch(matchResult, (id, match) => {
      if (match.left != null && match.right != null) {
        // The element is still there, but may have been moved
        this.updateElement(
          match.left as SModelElementImpl,
          match.right as SModelElementImpl,
          animationData,
        );
      } else if (match.right != null) {
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
        if (isFadeable(left) && match.leftParentId != null) {
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
