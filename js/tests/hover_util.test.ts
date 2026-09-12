/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import { HoverFeedbackAction } from 'sprotty-protocol';

import { hoverAfterFeedback, hoverFeedbackActions } from '../hover_util';

const enter = (id: string) =>
  HoverFeedbackAction.create({ mouseoverElement: id, mouseIsOver: true });
const leave = (id: string) =>
  HoverFeedbackAction.create({ mouseoverElement: id, mouseIsOver: false });

describe('hoverAfterFeedback', () => {
  it('enter sets the id, leave of that id clears to null', () => {
    const hovered: string | null = hoverAfterFeedback(null, enter('a'));
    expect(hovered).toBe('a');
    expect(hoverAfterFeedback(hovered, leave('a'))).toBeNull();
  });

  it('a stale leave for A cannot clear a newer B', () => {
    // DOM order is mouseout(A) then mouseover(B); a late leave(A) must be a no-op
    expect(hoverAfterFeedback('b', leave('a'))).toBe('b');
  });

  it('feedback for the current id is a no-op (no write-back loop)', () => {
    // the view's own dispatch from updateHover lands back in handle()
    expect(hoverAfterFeedback('a', enter('a'))).toBe('a');
    expect(hoverAfterFeedback(null, leave('a'))).toBeNull();
  });
});

describe('hoverFeedbackActions', () => {
  const pairs = (actions: HoverFeedbackAction[]) =>
    actions.map((a) => [a.mouseoverElement, a.mouseIsOver]);

  it('un-highlights the previous id and highlights the next', () => {
    expect(pairs(hoverFeedbackActions('a', 'b'))).toEqual([
      ['a', false],
      ['b', true],
    ]);
  });

  it('never dispatches null as an element id', () => {
    expect(pairs(hoverFeedbackActions('a', null))).toEqual([['a', false]]);
    expect(pairs(hoverFeedbackActions(null, 'a'))).toEqual([['a', true]]);
    expect(hoverFeedbackActions(undefined, null)).toEqual([]);
    expect(hoverFeedbackActions(null, null)).toEqual([]);
  });

  it('re-asserts an unchanged id without un-highlighting it first', () => {
    expect(pairs(hoverFeedbackActions('a', 'a'))).toEqual([['a', true]]);
  });
});
