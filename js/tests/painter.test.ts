/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { VNode } from 'snabbdom';
import { describe, expect, it } from 'vitest';

import { SNode, UpdateModelAction } from 'sprotty-protocol';

import { SGraphImpl, SNodeImpl, UpdateAnimationData, createFeatureSet } from 'sprotty';
// not re-exported from the package index
import { CssClassPostprocessor } from 'sprotty/lib/base/views/css-class-postprocessor';

import { ElkNode as ElkNodeJson } from '../sprotty/json/elkgraph-json';
import { ElkGraphJsonToSprotty } from '../sprotty/json/elkgraph-to-sprotty';
import { IElkSymbols } from '../sprotty/json/symbols';
import { ElkModelRenderer } from '../sprotty/renderer';
import { ElkNode } from '../sprotty/sprotty-model';
import { UpdateModelCommand2 } from '../sprotty/update/update-model';
import { ElkNodeView } from '../sprotty/views/node_views';

// UNIT tests (node, no browser): the ELK -> sprotty transform and a node view.

function layout(): ElkNodeJson {
  return {
    id: 'root',
    children: [
      {
        id: 'n1',
        x: 0,
        y: 0,
        width: 60,
        height: 30,
        properties: { cssClasses: 'base' },
        labels: [{ id: 'l1', text: 'n1' }],
        ports: [{ id: 'p1', x: 55, y: 10, width: 5, height: 5 }],
      },
      { id: 'n2', x: 100, y: 0, width: 60, height: 30 },
    ],
    edges: [{ id: 'e1', sources: ['n1'], targets: ['n2'] }],
  };
}
const SYMBOLS: IElkSymbols = {
  library: {
    sym: {
      id: 'sym',
      type: 'symbol',
      properties: {},
      element: { id: 'sym-el', children: [], properties: {} },
    },
  },
};

function classesById(graph: ReturnType<ElkGraphJsonToSprotty['transform']>) {
  const out: Record<string, string[] | undefined> = {};
  const walk = (el: SNode) => {
    out[el.id] = el.cssClasses;
    (el.children || []).forEach((c) => walk(c as SNode));
  };
  (graph.children || []).forEach((c) => walk(c as SNode));
  return out;
}

describe('painter styles in the ELK -> sprotty transform', () => {
  it('merges painted classes after the model classes on every kind of element', () => {
    const elk = layout();
    const before = JSON.stringify(elk);
    const graph = new ElkGraphJsonToSprotty().transform(elk, SYMBOLS, 'p', {
      n1: ['hl', 'base'], // `base` is already a model class: no duplicate
      l1: ['hl'],
      p1: ['warn'],
      e1: ['hl'],
      ghost: ['hl'], // not in the model: ignored here, `missing_ids()` in the kernel
      'sym-el': ['hl'], // a symbol-library element is not a model element
    });
    expect(classesById(graph)).toEqual({
      n1: ['base', 'hl'],
      p1: ['warn'],
      l1: ['hl'],
      n2: [],
      e1: ['hl'],
    });
    expect(graph.symbols.children?.map((c) => c.cssClasses)).toEqual([undefined]);
    // view-only: the kernel value the transform read is untouched
    expect(JSON.stringify(elk)).toBe(before);
    expect(before).not.toContain('hl');
  });

  it('is the plain transform without styles', () => {
    const graph = new ElkGraphJsonToSprotty().transform(layout(), SYMBOLS, 'p');
    expect(classesById(graph).n1).toEqual(['base']);
    expect(classesById(graph).n2).toEqual([]);
  });
});

describe('painted classes on the rendered element', () => {
  // Partial renderer fixture: hidden rendering bypasses viewport culling.
  type RenderContext = Pick<
    ElkModelRenderer,
    'targetKind' | 'hrefID' | 'renderChildren'
  >;
  const context: RenderContext = {
    targetKind: 'hidden',
    hrefID: () => undefined,
    renderChildren: () => [],
  };
  // The API requires a full renderer; keep the assertion at this fixture boundary.
  const asContext = (ctx: RenderContext) => ctx as ElkModelRenderer;

  it('lands as real classes (what the SVG exporter serializes)', () => {
    const root = new SGraphImpl();
    const node = new ElkNode();
    node.id = 'n1';
    node.type = 'node';
    node.size = { width: 60, height: 30 };
    node.position = { x: 0, y: 0 };
    node.properties = { cssClasses: 'base' };
    node.cssClasses = ['base', 'hl']; // what the transform produced
    root.add(node);
    const vnode = new ElkNodeView().render(node, asContext(context)) as VNode;
    new CssClassPostprocessor().decorate(vnode, node); // sprotty's default postprocessor
    expect(vnode.data?.class?.base).toBe(true);
    expect(vnode.data?.class?.hl).toBe(true);
    expect(node.properties.cssClasses).toBe('base'); // the model never learns `hl`
  });
});

describe('UpdateModelCommand2 keeps interaction state across a re-render', () => {
  function node(id: string): ElkNode {
    const n = new ElkNode();
    n.id = id;
    n.type = 'node';
    n.position = { x: 0, y: 0 };
    n.size = { width: 60, height: 30 };
    n.features = createFeatureSet(SNodeImpl.DEFAULT_FEATURES);
    return n;
  }
  it('carries hoverFeedback (and selected) from the old element to the new one', () => {
    const command = new UpdateModelCommand2(
      UpdateModelAction.create({ type: 'graph', id: 'root' }),
    );
    const left = node('n1');
    left.hoverFeedback = true;
    left.selected = true;
    const right = node('n1');
    const animation: UpdateAnimationData = { fades: [] };
    // `updateElement` is protected: element access is the documented TS escape hatch
    command['updateElement'](left, right, animation);
    expect(right.hoverFeedback).toBe(true);
    expect(right.selected).toBe(true);
    expect(animation.moves).toBeUndefined(); // same place: nothing animates
  });
});
