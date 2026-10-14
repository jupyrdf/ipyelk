/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { afterEach, describe, expect, it } from 'vitest';

import { Action, SelectAction } from 'sprotty-protocol';

import { MouseTool, SModelRootImpl, SNodeImpl, createFeatureSet } from 'sprotty';
import { DOMHelper } from 'sprotty/lib/base/views/dom-helper';

import { ElkNode } from '../sprotty/sprotty-model';
import { NodeSelectToolMouseListener, isJLWidget } from '../tools/select';

// UNIT test (happy-dom): the DOM `SGraphView` and `ElkModelRenderer` render,
// without snabbdom. The diagram's own view element has the `jupyter-widgets`
// class too, outside the overlay containers. The container of a widget or
// html node carries the node's DOM id (`renderJLNodeWidgets` decorates it),
// the control overlay's container does not.
function diagram(prefix: string, parent: Element = document.body) {
  const view = el(parent, 'div', 'jupyter-widgets jp-ElkView');
  const root = el(view, 'div', 'sprotty-root', `${prefix}_root`);
  const control = el(el(root, 'div', 'sprotty-overlay'), 'div', 'elkcontainer');
  const box = el(control, 'div', 'jupyter-widgets widget-vbox');
  const button = el(box, 'button', 'jupyter-widgets widget-button');
  const icon = el(button, 'i', 'fa fa-plus');
  const svg = el(root, 'svg', 'sprotty-graph');
  const node = el(svg, 'g', 'elknode', `${prefix}_n1`);
  const nodes = el(root, 'div', 'sprotty-overlay');
  const container = el(nodes, 'div', 'elkcontainer', `${prefix}_w1`);
  const slider = el(container, 'div', 'jupyter-widgets widget-slider');
  const handle = el(slider, 'div', 'noUi-handle');
  const html = el(el(nodes, 'div', 'elkcontainer', `${prefix}_h1`), 'h1', '');
  return { view, root, button, icon, node, container, handle, html };
}

function el(parent: Element, tag: string, classes: string, id?: string) {
  const child =
    tag === 'svg' || tag === 'g'
      ? document.createElementNS('http://www.w3.org/2000/svg', tag)
      : document.createElement(tag);
  child.setAttribute('class', classes);
  if (id) child.id = id;
  parent.appendChild(child);
  return child;
}

function mouseUp(target: Element) {
  target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button: 0 }));
}

/** `isJLWidget` as the diagram whose root handles the bubbling mouseup sees it */
function seenBy(root: Element, target: Element) {
  let seen: boolean | undefined;
  root.addEventListener('mouseup', (event) => (seen = isJLWidget(event)), {
    once: true,
  });
  mouseUp(target);
  return seen;
}

afterEach(() => document.body.replaceChildren());

describe('isJLWidget', () => {
  it('sees a click on an element inside an overlay widget', () => {
    const d = diagram('a');
    expect(seenBy(d.root, d.icon)).toBe(true);
    expect(seenBy(d.root, d.button)).toBe(true);
    expect(seenBy(d.root, d.handle)).toBe(true);
  });

  it('does not see a click on the diagram, inside its jupyter-widgets view', () => {
    const d = diagram('a');
    expect(seenBy(d.root, d.node)).toBe(false);
    expect(seenBy(d.root, d.root)).toBe(false);
    expect(seenBy(d.view, d.view)).toBe(false);
  });

  it('does not see a click on html node markup', () => {
    const d = diagram('a');
    expect(seenBy(d.root, d.html)).toBe(false);
  });

  it('scopes the widget to the diagram that handles the event', () => {
    const outer = diagram('a');
    const inner = diagram('b', outer.container);
    // the inner diagram is a widget of the outer one, not of itself
    expect(seenBy(inner.root, inner.node)).toBe(false);
    expect(seenBy(outer.root, inner.node)).toBe(true);
    expect(seenBy(inner.root, inner.icon)).toBe(true);
    expect(seenBy(outer.root, inner.icon)).toBe(true);
  });

  it('does not scope without a current target', () => {
    const d = diagram('a');
    expect(isJLWidget({ target: d.icon, currentTarget: null })).toBe(true);
    expect(isJLWidget({ target: d.node, currentTarget: null })).toBe(false);
  });

  it('is false without an element target', () => {
    expect(isJLWidget({ target: null, currentTarget: null })).toBe(false);
    expect(isJLWidget({} as Event)).toBe(false);
    const text = document.createTextNode('x');
    expect(isJLWidget({ target: text, currentTarget: null })).toBe(false);
  });
});

describe('NodeSelectToolMouseListener', () => {
  type Diagram = ReturnType<typeof diagram>;

  function node(model: SModelRootImpl, id: string) {
    const n = new ElkNode();
    n.id = id;
    n.type = 'node';
    n.features = createFeatureSet(SNodeImpl.DEFAULT_FEATURES);
    model.add(n);
  }

  /** Selection changes sprotty's `MouseTool` dispatches after the mouseup. */
  function selectionAfterMouseUp(
    pick: (d: Diagram) => Element,
    button = 0,
    selectedIDs: string[] = [],
  ) {
    const model = new SModelRootImpl();
    model.id = 'root';
    for (const id of ['n1', 'w1', 'h1']) node(model, id);
    for (const id of selectedIDs) (model.index.getById(id) as ElkNode).selected = true;
    const dispatched: Action[] = [];
    const tool = Object.assign(
      new MouseTool([new NodeSelectToolMouseListener('node', {} as any)]),
      {
        domHelper: Object.assign(new DOMHelper(), { viewerOptions: { baseDiv: 'c' } }),
        actionDispatcher: { dispatch: (action: Action) => dispatched.push(action) },
      },
    );
    const d = diagram('c');
    // as `MouseTool.decorate` binds it on the root's vnode
    d.root.addEventListener(
      'mouseup',
      (event) => tool.mouseUp(model, event as MouseEvent),
      { once: true },
    );
    pick(d).dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button }));
    return {
      actionCount: dispatched.length,
      selectedElementsIDs: (dispatched as SelectAction[]).flatMap(
        (a) => a.selectedElementsIDs,
      ),
      deselectedElementsIDs: (dispatched as SelectAction[]).flatMap(
        (a) => a.deselectedElementsIDs,
      ),
    };
  }

  it('selects the node under a click on the diagram', () => {
    expect(selectionAfterMouseUp((d) => d.node)).toEqual({
      actionCount: 1,
      selectedElementsIDs: ['n1'],
      deselectedElementsIDs: [],
    });
    expect(selectionAfterMouseUp((d) => d.html)).toEqual({
      actionCount: 1,
      selectedElementsIDs: ['h1'],
      deselectedElementsIDs: [],
    });
  });

  it('selects nothing on a right click on a node', () => {
    expect(selectionAfterMouseUp((d) => d.node, 2)).toEqual({
      actionCount: 1,
      selectedElementsIDs: [],
      deselectedElementsIDs: [],
    });
  });

  it('preserves the existing selection on a click inside a widget node', () => {
    expect(selectionAfterMouseUp((d) => d.handle, 0, ['n1'])).toEqual({
      actionCount: 1,
      selectedElementsIDs: [],
      deselectedElementsIDs: [],
    });
  });

  // the control overlay's container has no DOM id: sprotty resolves a click
  // there to the unselectable root, so this held before #216 too
  it('preserves the existing selection on a control overlay button icon click', () => {
    expect(selectionAfterMouseUp((d) => d.icon, 0, ['n1'])).toEqual({
      actionCount: 0,
      selectedElementsIDs: [],
      deselectedElementsIDs: [],
    });
  });
});
