/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import { FirstFit, IFirstFitHost, fitTargets } from '../first_fit';
import { ElkNode } from '../sprotty/json/elkgraph-json';

const LAYOUT: ElkNode = {
  id: 'root',
  children: [
    { id: 'a', x: 0, y: 0, width: 10, height: 10, children: [{ id: 'a1' }] },
    { id: 'b', x: 50, y: 0, width: 10, height: 10 },
  ],
  edges: [{ id: 'e', sources: ['a'], targets: ['b'] }],
};

const EMPTY: ElkNode = { id: 'root', children: [] };

/** A host that records what the view would do. */
function host(shown = true, enabled = true) {
  const calls: string[] = [];
  const fits: string[][] = [];
  const h: IFirstFitHost & { shown: boolean; enabled: boolean } = {
    shown,
    enabled,
    isEnabled: () => h.enabled,
    isShown: () => h.shown,
    fit: (ids) => {
      calls.push('fit');
      fits.push(ids);
    },
    watch: () => calls.push('watch'),
    unwatch: () => calls.push('unwatch'),
  };
  return { h, calls, fits };
}

describe('fitTargets', () => {
  it('frames the top-level nodes and edges', () => {
    expect(fitTargets(LAYOUT)).toEqual(['a', 'b', 'e']);
  });

  it('has nothing to frame without a sized node', () => {
    expect(fitTargets(null)).toEqual([]);
    expect(fitTargets(EMPTY)).toEqual([]);
    expect(fitTargets({ id: 'root', children: [{ id: 'a' }] })).toEqual([]);
    expect(
      fitTargets({ id: 'root', children: [{ id: 'a', width: 0, height: 5 }] }),
    ).toEqual([]);
  });
});

describe('FirstFit', () => {
  it('fits a shown view once, after its first layout', () => {
    const { h, calls, fits } = host();
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    first.afterLayout(LAYOUT); // a re-layout must not move a camera the user owns
    first.revealed();
    expect(fits).toEqual([['a', 'b', 'e']]);
    expect(calls).toEqual(['fit']); // a shown view never watches
    expect(first.state).toBe('done');
  });

  it('does nothing while disabled, and stays done when enabled later', () => {
    const { h, fits } = host(true, false);
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    h.enabled = true;
    first.afterLayout(LAYOUT);
    expect(fits).toEqual([]);
    expect(first.state).toBe('done');
  });

  it('waits for a layout with something to frame', () => {
    const { h, fits } = host();
    const first = new FirstFit(h);
    first.afterLayout(null);
    first.afterLayout(EMPTY);
    expect(fits).toEqual([]);
    expect(first.state).toBe('layout');
    first.afterLayout(LAYOUT);
    expect(fits).toEqual([['a', 'b', 'e']]);
  });

  it('defers a hidden view until it is first revealed', () => {
    const { h, calls, fits } = host(false);
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    expect(first.state).toBe('reveal');
    expect(calls).toEqual(['watch']);
    first.revealed(); // a resize while still hidden
    expect(fits).toEqual([]);
    h.shown = true;
    first.revealed();
    expect(fits).toEqual([['a', 'b', 'e']]);
    expect(calls).toEqual(['watch', 'unwatch', 'fit']);
    // hiding and showing again keeps the user's camera
    h.shown = false;
    first.revealed();
    h.shown = true;
    first.revealed();
    expect(fits).toHaveLength(1);
  });

  it('frames the latest layout when revealed', () => {
    const { h, fits } = host(false);
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    first.afterLayout({ ...LAYOUT, edges: [] });
    h.shown = true;
    first.revealed();
    expect(fits).toEqual([['a', 'b']]);
  });

  it('drops a deferred fit disabled before the reveal', () => {
    const { h, calls, fits } = host(false);
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    h.enabled = false;
    h.shown = true;
    first.revealed();
    expect(fits).toEqual([]);
    expect(calls).toEqual(['watch', 'unwatch']);
    expect(first.state).toBe('done');
  });

  it('yields a deferred fit to an explicit camera', () => {
    const { h, calls, fits } = host(false);
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    first.cancel();
    h.shown = true;
    first.revealed();
    expect(fits).toEqual([]);
    expect(calls).toEqual(['watch', 'unwatch']);
  });

  it('keeps a pending first fit across an explicit camera before any layout', () => {
    // the first model replaces the root, and with it any camera set before it
    const { h, fits } = host();
    const first = new FirstFit(h);
    first.cancel();
    first.afterLayout(LAYOUT);
    expect(fits).toHaveLength(1);
  });

  it('stops watching when disposed', () => {
    const { h, calls, fits } = host(false);
    const first = new FirstFit(h);
    first.afterLayout(LAYOUT);
    first.dispose();
    h.shown = true;
    first.revealed();
    first.afterLayout(LAYOUT);
    expect(fits).toEqual([]);
    expect(calls).toEqual(['watch', 'unwatch']);
  });
});
