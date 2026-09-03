/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import { canonicalSelection, selectionDelta } from '../selection_util';

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
