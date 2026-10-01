/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { HoverFeedbackAction } from 'sprotty-protocol';

/**
 * The kernel-facing hovered id after a sprotty `HoverFeedbackAction`.
 *
 * Enter always wins. Leave only clears when the departed element is STILL the
 * hovered one: pointer events arrive in DOM order (`mouseout` A, `mouseover` B),
 * but a leave for A that lands after B was entered must not erase B.
 */
export function hoverAfterFeedback(
  current: string | null,
  action: Pick<HoverFeedbackAction, 'mouseoverElement' | 'mouseIsOver'>,
): string | null {
  if (action.mouseIsOver) {
    return action.mouseoverElement;
  }
  return current === action.mouseoverElement ? null : current;
}

/**
 * Feedback to dispatch when the kernel's `hovered_id` changes: un-highlight
 * the previous element, highlight the next. `null` is "nothing hovered" and is
 * never sent to sprotty as an element id.
 */
export function hoverFeedbackActions(
  previous: string | null | undefined,
  next: string | null | undefined,
): HoverFeedbackAction[] {
  const actions: HoverFeedbackAction[] = [];
  if (previous != null && previous !== next) {
    actions.push(
      HoverFeedbackAction.create({ mouseoverElement: previous, mouseIsOver: false }),
    );
  }
  if (next != null) {
    actions.push(
      HoverFeedbackAction.create({ mouseoverElement: next, mouseIsOver: true }),
    );
  }
  return actions;
}
