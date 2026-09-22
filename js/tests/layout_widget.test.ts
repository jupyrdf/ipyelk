/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it, vi } from 'vitest';

import {
  RunQueue,
  applyProperties,
  collectProperties,
  layoutErrorMessage,
  prepareGraphForElk,
  staleMessage,
} from '../layout_widget_util';

/** a small graph with `properties` on every element kind */
function makeGraph(): any {
  return {
    id: 'root',
    properties: { cssClasses: 'sysml-diagram' },
    children: [
      {
        id: 'n1',
        properties: { cssClasses: 'node blue' },
        ports: [{ id: 'n1.p0', properties: { cssClasses: 'port' } }],
        labels: [{ id: 'n1.l0', properties: { cssClasses: 'label' } }],
      },
      { id: 'n2', properties: { cssClasses: 'node green' } },
    ],
    edges: [
      {
        id: 'e0',
        sources: ['n1'],
        targets: ['n2'],
        properties: { cssClasses: 'edge dashed' },
      },
    ],
  };
}

describe('layoutErrorMessage', () => {
  it('wraps an error into a kernel error message', () => {
    const msg = layoutErrorMessage(new Error('elk exploded'));
    expect(msg.action).toBe('error');
    expect(msg.error).toContain('elk exploded');
  });
});

describe('prepareGraphForElk', () => {
  it('strips properties from the copy and collects them all', () => {
    const { graph, propmap } = prepareGraphForElk(makeGraph());
    expect(graph.properties).toBeUndefined();
    expect(graph.children[0].properties).toBeUndefined();
    expect(graph.children[0].ports[0].properties).toBeUndefined();
    expect(graph.edges[0].properties).toBeUndefined();
    for (const id of ['root', 'n1', 'n1.p0', 'n1.l0', 'n2', 'e0']) {
      expect(propmap[id]).toBeDefined();
    }
    expect(propmap['e0'].cssClasses).toBe('edge dashed');
  });

  it('does not mutate the caller graph (shared inlet value)', () => {
    const inlet = makeGraph();
    prepareGraphForElk(inlet);
    expect(inlet).toEqual(makeGraph());
  });

  it('is idempotent: a duplicate run sees the same properties', () => {
    // regression: layout() used to strip the inlet value in place, so a
    // resent `run` message collected `undefined` for every element and
    // pushed a style-less (black-and-white) layout
    const inlet = makeGraph();
    const first = prepareGraphForElk(inlet);
    const second = prepareGraphForElk(inlet);
    expect(second.propmap['n1']).toEqual(first.propmap['n1']);
    expect(second.propmap['n1'].cssClasses).toBe('node blue');
  });

  it('round-trips through applyProperties onto a layout result', () => {
    const { graph, propmap } = prepareGraphForElk(makeGraph());
    const restored = applyProperties(graph, propmap);
    expect(restored.children[1].properties.cssClasses).toBe('node green');
    expect(restored.edges[0].properties.cssClasses).toBe('edge dashed');
  });
});

describe('collectProperties', () => {
  it('documents the in-place strip it performs', () => {
    const graph = makeGraph();
    const propmap = collectProperties(graph);
    expect(graph.properties).toBeUndefined(); // mutated -- by design
    expect(propmap['root'].cssClasses).toBe('sysml-diagram');
  });
});

describe('staleMessage', () => {
  // the browser -> kernel half of the stale re-sync protocol: SyncedPipe
  // answers `action: stale` by re-sending the pipe's (and endpoints') state
  it('is null when the run request is servable', () => {
    expect(staleMessage({}, { id: 'root' }, {})).toBeNull();
  });

  it('reports which of inlet / value / outlet never arrived', () => {
    expect(staleMessage(undefined, undefined, {})).toEqual({
      action: 'stale',
      missing: { inlet: true, value: true, outlet: false },
    });
    expect(staleMessage({}, undefined, {})).toEqual({
      action: 'stale',
      missing: { inlet: false, value: true, outlet: false },
    });
    expect(staleMessage({}, { id: 'root' }, null)).toEqual({
      action: 'stale',
      missing: { inlet: false, value: false, outlet: true },
    });
  });
});

describe('RunQueue', () => {
  // the browser half of the roundtrip generation: the kernel re-sends `run`
  // with backoff until answered, so a slow layout must not be computed once
  // per resend, and a newer request must run once after the current one
  function makeQueue() {
    const started: number[] = [];
    const gates: Record<number, () => void> = {};
    const queue = new RunQueue((gen) => {
      started.push(gen);
      return new Promise<void>((resolve) => {
        gates[gen] = resolve;
      });
    });
    return { queue, started, gates };
  }

  async function settle() {
    for (let i = 0; i < 4; i++) {
      await Promise.resolve();
    }
  }

  it('ignores a re-sent request for the in-flight generation', async () => {
    const { queue, started, gates } = makeQueue();
    expect(queue.request(1)).toBe('started');
    expect(queue.request(1)).toBe('ignored');
    expect(queue.request(1)).toBe('ignored');
    expect(started).toEqual([1]);
    gates[1]();
    await settle();
    expect(queue.current).toBeNull();
    expect(started).toEqual([1]);
  });

  it('queues only the newest generation and starts it once the current resolves', async () => {
    const { queue, started, gates } = makeQueue();
    queue.request(1);
    expect(queue.request(2)).toBe('queued');
    expect(queue.request(3)).toBe('queued');
    expect(queue.request(3)).toBe('ignored');
    expect(queue.pending).toBe(3);
    expect(started).toEqual([1]);
    gates[1]();
    await settle();
    expect(started).toEqual([1, 3]);
    expect(queue.current).toBe(3);
    expect(queue.pending).toBeNull();
    gates[3]();
    await settle();
    expect(queue.current).toBeNull();
  });

  it('drops a request older than the in-flight or queued generation', async () => {
    const { queue, started, gates } = makeQueue();
    queue.request(3);
    expect(queue.request(2)).toBe('ignored');
    queue.request(5);
    expect(queue.request(4)).toBe('ignored');
    gates[3]();
    await settle();
    expect(started).toEqual([3, 5]);
  });

  it('coalesces unversioned requests (older kernel) into one trailing run', async () => {
    const { queue, started, gates } = makeQueue();
    expect(queue.request(undefined)).toBe('started');
    expect(queue.request(undefined)).toBe('queued');
    expect(queue.request(undefined)).toBe('ignored');
    gates[0]();
    await settle();
    expect(started).toEqual([0, 0]);
  });

  it('moves on when start throws or rejects', async () => {
    const started: number[] = [];
    const queue = new RunQueue((gen) => {
      started.push(gen);
      if (gen === 1) {
        throw new Error('sync');
      }
      return Promise.reject(new Error('async'));
    });
    queue.request(1);
    queue.request(2);
    await settle();
    expect(started).toEqual([1, 2]);
    await settle();
    expect(queue.current).toBeNull();
    expect(queue.request(3)).toBe('started');
  });
});
