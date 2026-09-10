/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import {
  canonicalSelection,
  selectionAfterLayout,
  selectionDelta,
} from '../selection_util';

describe('selectionDelta', () => {
  it('reports what entered and what left', () => {
    const { entering, exiting, changed } = selectionDelta(['a', 'b'], ['b', 'c']);
    expect(entering).toEqual(['c']);
    expect(exiting).toEqual(['a']);
    expect(changed).toBe(true);
  });

  it('treats a reordering as no change', () => {
    // the write-back that pegged the renderer: two views of one model gather
    // the same selection in different orders and dispatch at each other
    expect(selectionDelta(['a', 'b', 'c'], ['c', 'a', 'b']).changed).toBe(false);
    expect(selectionDelta(['a', 'b', 'c'], ['c', 'a', 'b']).entering).toEqual([]);
    expect(selectionDelta(['a', 'b', 'c'], ['c', 'a', 'b']).exiting).toEqual([]);
  });

  it('treats duplicates as no change', () => {
    expect(selectionDelta(['a'], ['a', 'a']).changed).toBe(false);
  });

  it('handles an unset previous selection', () => {
    expect(selectionDelta(undefined, ['a']).changed).toBe(true);
    expect(selectionDelta(undefined, ['a']).entering).toEqual(['a']);
    expect(selectionDelta(['a'], undefined).exiting).toEqual(['a']);
    expect(selectionDelta(undefined, undefined).changed).toBe(false);
  });
});

describe('canonicalSelection', () => {
  it('does not depend on the gathering order', () => {
    expect(canonicalSelection(['c', 'a', 'b'])).toEqual(
      canonicalSelection(['b', 'c', 'a']),
    );
  });

  it('drops duplicates and tolerates nothing', () => {
    expect(canonicalSelection(['b', 'a', 'b'])).toEqual(['a', 'b']);
    expect(canonicalSelection(undefined)).toEqual([]);
  });
});

// Pure selection policy; the browser checks exercise its model-submission wiring.
describe('selectionAfterLayout', () => {
  const exists = (id: string) => id !== 'gone';

  it('replays queued selections over live ids', () => {
    expect(selectionAfterLayout(['n1', 'gone'], ['ignored'], exists)).toEqual(['n1']);
  });

  it('uses live ids when no selection was queued', () => {
    expect(selectionAfterLayout(null, ['n1', 'n2', 'gone'], exists)).toEqual([
      'n1',
      'n2',
    ]);
  });

  it('preserves an empty kernel selection', () => {
    expect(selectionAfterLayout([], ['n1'], exists)).toEqual([]);
    expect(selectionAfterLayout(null, [], exists)).toEqual([]);
  });

  it('selects nothing when ids are absent or there is no selection tool', () => {
    expect(selectionAfterLayout(null, ['gone'], exists)).toEqual([]);
    expect(selectionAfterLayout(null, undefined, exists)).toEqual([]);
    expect(selectionAfterLayout(undefined, null, exists)).toEqual([]);
  });
});
