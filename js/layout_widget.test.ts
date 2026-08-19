/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import {
  applyProperties,
  collectProperties,
  layoutErrorMessage,
  prepareGraphForElk,
} from './layout_widget_util';

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
