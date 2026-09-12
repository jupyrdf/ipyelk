/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { VNode } from 'snabbdom';
import { describe, expect, it } from 'vitest';

import { SGraphImpl } from 'sprotty';

import { ElkProperties } from '../sprotty/json/elkgraph-json';
import { ElkModelRenderer } from '../sprotty/renderer';
import { ElkLabel, ElkNode } from '../sprotty/sprotty-model';
import { ElkLabelView, ElkNodeView } from '../sprotty/views/node_views';

// Partial renderer fixture: hidden rendering bypasses viewport culling,
// hrefID selects text labels, and renderChildren omits unrelated children.
type RenderContext = Pick<ElkModelRenderer, 'targetKind' | 'hrefID' | 'renderChildren'>;
const context: RenderContext = {
  targetKind: 'hidden',
  hrefID: () => undefined,
  renderChildren: () => [],
};
// The API requires a full renderer; keep the assertion at this fixture boundary.
const asContext = (ctx: RenderContext) => ctx as ElkModelRenderer;

function renderLabel(properties: ElkProperties | undefined): VNode {
  const root = new SGraphImpl(); // a viewport root: `isVisible` reads `root.zoom`
  const label = new ElkLabel();
  label.id = 'l0';
  label.type = 'label';
  label.text = 'shown text';
  label.size = { width: 10, height: 10 };
  label.position = { x: 0, y: 0 };
  label.properties = properties;
  root.add(label);
  return new ElkLabelView().render(label, asContext(context)) as VNode;
}

function titleVNode(vnode: VNode): VNode | undefined {
  return ((vnode.children as VNode[]) || []).find((c) => c?.sel === 'title');
}

describe('ElkLabelView tooltip', () => {
  it('renders properties.tooltip as the svg <title> hover text', () => {
    const vnode = renderLabel({ tooltip: 'the full, untruncated text' });
    expect(vnode.sel).toBe('text');
    const title = titleVNode(vnode);
    expect(title?.text).toBe('the full, untruncated text');
    // the label text is still rendered, as a sibling text node after the title
    const texts = (vnode.children as VNode[]).map((c) => c.text);
    expect(texts).toEqual(['the full, untruncated text', 'shown text']);
  });

  it('renders no <title> without a tooltip', () => {
    for (const props of [{}, undefined, { tooltip: '' }]) {
      const vnode = renderLabel(props);
      expect(titleVNode(vnode)).toBeUndefined();
      // single text child: sprotty's svg helper folds it into vnode.text
      expect(vnode.text).toBe('shown text');
      expect(vnode.children).toBeUndefined();
    }
  });

  it('carries arbitrary tooltip text as a text node, never as markup', () => {
    const hostile = '<script>alert(1)</script> & "quotes"';
    const vnode = renderLabel({ tooltip: hostile });
    const title = titleVNode(vnode);
    expect(title?.text).toBe(hostile); // verbatim: snabbdom creates a DOM text node
    expect(title?.children).toBeUndefined(); // no parsed <script> element
    expect(title?.data?.props?.innerHTML).toBeUndefined();
    expect(vnode.data?.props?.innerHTML).toBeUndefined();
  });
});

describe('ElkNodeView label separator', () => {
  function makeNode(
    width: number | undefined,
    labels: { y: number; properties?: ElkProperties }[],
  ) {
    const root = new SGraphImpl();
    const node = new ElkNode();
    node.id = 'n0';
    node.type = 'node';
    node.size = { width, height: 40 };
    node.position = { x: 0, y: 0 };
    node.properties = {};
    root.add(node);
    labels.forEach((l, i) => {
      const label = new ElkLabel();
      label.id = `l${i}`;
      label.type = 'label';
      label.text = `t${i}`;
      label.size = { width: 10, height: 10 };
      label.position = { x: 2, y: l.y };
      label.properties = l.properties;
      node.add(label);
    });
    return node;
  }

  // the node view's rendered <g> children: [mark, <g.elkchildren>, ...separators]
  function renderNode(node: ElkNode): VNode {
    return new ElkNodeView().render(node, asContext(context)) as VNode;
  }
  function renderSeparatorPaths(node: ElkNode): VNode[] {
    return (renderNode(node).children as VNode[]).filter((c) => c?.sel === 'path');
  }

  it('draws one full-width rule 1px above each opted-in label', () => {
    const node = makeNode(120, [
      { y: 5, properties: { separator: true } },
      { y: 20 }, // unmarked: unchanged, no rule
      { y: 30, properties: { separator: true } },
    ]);
    const paths = renderSeparatorPaths(node);
    expect(paths.map((p) => p.data?.attrs?.d)).toEqual([
      'M 0,4 L 120,4',
      'M 0,29 L 120,29',
    ]);
    expect(paths.every((p) => p.data?.class?.elkseparator === true)).toBe(true);
  });

  it('uses a label-provided separator gap when supplied by Python', () => {
    const node = makeNode(120, [
      { y: 20, properties: { separator: true, separatorGap: 2.5 } },
    ]);
    expect(renderSeparatorPaths(node).map((p) => p.data?.attrs?.d)).toEqual([
      'M 0,17.5 L 120,17.5',
    ]);
  });

  it('draws nothing for unmarked, false, or non-boolean-true labels', () => {
    // the kernel-side `separator: bool | None` schema cannot produce 'true'
    // (the string) but the wire format is untyped JSON: model it as such
    const stringTrue = JSON.parse('{"separator": "true"}') as ElkProperties;
    const node = makeNode(120, [
      { y: 5 },
      { y: 10, properties: {} },
      { y: 15, properties: { separator: false } },
      { y: 20, properties: stringTrue },
    ]);
    expect(renderSeparatorPaths(node)).toEqual([]);
    // and the vnode shape is exactly the pre-separator one: [mark, children]
    const g = renderNode(node);
    expect((g.children as VNode[]).map((c) => c.sel)).toEqual(['rect', 'g']);
  });

  it('draws no rule when the node width is not a finite positive number', () => {
    // `undefined`: a node whose size never arrived (the view guards `size?.width`)
    for (const width of [0, -5, NaN, Infinity, undefined]) {
      const node = makeNode(width, [{ y: 5, properties: { separator: true } }]);
      expect(renderSeparatorPaths(node)).toEqual([]);
    }
  });
});
