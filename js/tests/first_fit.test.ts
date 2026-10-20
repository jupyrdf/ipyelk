/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  FirstFit,
  IFirstFitHost,
  elementFirstFitHost,
  fitTargets,
} from '../first_fit';
import { ElkNode } from '../sprotty/json/elkgraph-json';

const LAYOUT: ElkNode = {
  id: 'root',
  children: [
    { id: 'a', x: 0, y: 0, width: 10, height: 10, children: [{ id: 'a1' }] },
    {
      id: 'b',
      x: 50,
      y: 0,
      width: 10,
      height: 10,
      // ELK puts ports, and their labels, outside the node
      ports: [{ id: 'p', x: 10, y: 2, width: 4, height: 4, labels: [{ id: 'pl' }] }],
    },
  ],
  edges: [{ id: 'e', sources: ['a'], targets: ['b'] }],
};

const ALL = ['a', 'a1', 'b', 'p', 'pl', 'e'];

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
  it('frames every element, ports and labels included', () => {
    expect(fitTargets(LAYOUT)).toEqual(['a', 'a1', 'b', 'p', 'pl', 'e']);
  });

  it('leaves out the slack elements that stand in for hidden ones', () => {
    const slack = { cssClasses: 'slack-port' };
    const layout = {
      ...LAYOUT,
      children: [{ ...LAYOUT.children[0], ports: [{ id: 'x.slack', properties: slack }] }],
      edges: [],
    };
    expect(fitTargets(layout)).toEqual(['a', 'a1']);
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
    expect(fits).toEqual([ALL]);
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
    expect(fits).toEqual([ALL]);
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
    expect(fits).toEqual([ALL]);
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
    expect(fits).toEqual([['a', 'a1', 'b', 'p', 'pl']]);
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

describe('elementFirstFitHost', () => {
  /** An element of the given size, attached to the page or not. */
  function element(width: number, height: number, isConnected = true) {
    return {
      isConnected,
      getBoundingClientRect: () => ({ width, height }),
    } as unknown as HTMLElement;
  }

  /** A stand-in `ResizeObserver` that records its instances. */
  class FakeObserver {
    static made: FakeObserver[] = [];
    observed: unknown[] = [];
    disconnected = false;
    constructor(readonly callback: () => void) {
      FakeObserver.made.push(this);
    }
    observe(el: unknown) {
      this.observed.push(el);
    }
    disconnect() {
      this.disconnected = true;
    }
  }

  afterEach(() => {
    vi.unstubAllGlobals();
    FakeObserver.made = [];
  });

  it('is shown only with a size on the page', () => {
    const shown = (el: HTMLElement) =>
      elementFirstFitHost(() => el, () => true, () => null, () => null).isShown();
    expect(shown(element(100, 50))).toBe(true);
    expect(shown(element(0, 0))).toBe(false); // display: none, or a scale(0) tab
    expect(shown(element(100, 0))).toBe(false);
    expect(shown(element(100, 50, false))).toBe(false);
  });

  it('observes the element once until unwatched, and reports reveals', () => {
    vi.stubGlobal('ResizeObserver', FakeObserver);
    const el = element(0, 0);
    let reveals = 0;
    const h = elementFirstFitHost(() => el, () => true, () => null, () => reveals++);
    h.watch();
    h.watch();
    expect(FakeObserver.made).toHaveLength(1);
    expect(FakeObserver.made[0].observed).toEqual([el]);
    FakeObserver.made[0].callback();
    expect(reveals).toBe(1);
    h.unwatch();
    expect(FakeObserver.made[0].disconnected).toBe(true);
    h.watch();
    expect(FakeObserver.made).toHaveLength(2);
  });

  it('drives FirstFit from a CSS reveal to one fit, and lets go of the observer', () => {
    vi.stubGlobal('ResizeObserver', FakeObserver);
    let size = 0;
    const el = {
      isConnected: true,
      getBoundingClientRect: () => ({ width: size, height: size }),
    } as unknown as HTMLElement;
    const fits: string[][] = [];
    const first: FirstFit = new FirstFit(
      elementFirstFitHost(
        () => el,
        () => true,
        (ids) => fits.push(ids),
        () => first.revealed(),
      ),
    );
    first.afterLayout(LAYOUT);
    const [observer] = FakeObserver.made;
    observer.callback(); // still hidden
    expect(fits).toEqual([]);
    size = 300;
    observer.callback();
    expect(fits).toEqual([ALL]);
    expect(observer.disconnected).toBe(true);
  });

  it('does without an observer where there is none', () => {
    vi.stubGlobal('ResizeObserver', undefined);
    const h = elementFirstFitHost(() => element(0, 0), () => true, () => null, () => null);
    expect(() => h.watch()).not.toThrow();
    expect(() => h.unwatch()).not.toThrow();
  });
});
