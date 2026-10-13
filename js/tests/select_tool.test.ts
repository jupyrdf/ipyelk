/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { describe, expect, it } from 'vitest';

import { SelectAction } from 'sprotty-protocol';

import { SModelRootImpl, SNodeImpl, createFeatureSet } from 'sprotty';

import { ElkNode } from '../sprotty/sprotty-model';
import { NodeSelectToolMouseListener, isJLWidget } from '../tools/select';

// UNIT test (happy-dom): the DOM a diagram view renders, without sprotty.
// The view element of a widget has the `jupyter-widgets` class, and so does
// the diagram's own view element, outside the overlay containers.
function diagram(parent: Element = document.body) {
  const view = el(parent, 'div', 'jupyter-widgets jp-ElkView');
  const root = el(view, 'div', 'sprotty-root');
  const overlay = el(root, 'div', 'sprotty-overlay');
  const container = el(overlay, 'div', 'elkcontainer');
  const box = el(container, 'div', 'jupyter-widgets widget-vbox');
  const button = el(box, 'button', 'jupyter-widgets widget-button');
  const icon = el(button, 'i', 'fa fa-plus');
  const svg = el(root, 'svg', 'sprotty-graph');
  const node = el(svg, 'g', 'elknode');
  return { view, root, container, button, icon, node };
}

function el(parent: Element, tag: string, classes: string) {
  const child =
    tag === 'svg' || tag === 'g'
      ? document.createElementNS('http://www.w3.org/2000/svg', tag)
      : document.createElement(tag);
  child.setAttribute('class', classes);
  parent.appendChild(child);
  return child;
}

/** `isJLWidget` as the diagram whose root handles the bubbling mouseup sees it */
function seenBy(root: Element, target: Element) {
  let seen: boolean | undefined;
  root.addEventListener('mouseup', (event) => (seen = isJLWidget(event)), {
    once: true,
  });
  target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button: 0 }));
  return seen;
}

describe('isJLWidget', () => {
  it('sees a click on an element inside an overlay widget', () => {
    const d = diagram();
    expect(seenBy(d.root, d.icon)).toBe(true);
    expect(seenBy(d.root, d.button)).toBe(true);
  });

  it('does not see a click on the diagram, inside its jupyter-widgets view', () => {
    const d = diagram();
    expect(seenBy(d.root, d.node)).toBe(false);
    expect(seenBy(d.root, d.root)).toBe(false);
    expect(seenBy(d.view, d.view)).toBe(false);
  });

  it('scopes the widget to the diagram that handles the event', () => {
    const outer = diagram();
    const inner = diagram(outer.container);
    // the inner diagram is a widget of the outer one, not of itself
    expect(seenBy(inner.root, inner.node)).toBe(false);
    expect(seenBy(outer.root, inner.node)).toBe(true);
    expect(seenBy(inner.root, inner.icon)).toBe(true);
    expect(seenBy(outer.root, inner.icon)).toBe(true);
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

  function selectedAfterMouseUp(pick: (d: Diagram) => Element) {
    const model = new SModelRootImpl();
    const node = new ElkNode();
    node.id = 'n1';
    node.type = 'node';
    node.features = createFeatureSet(SNodeImpl.DEFAULT_FEATURES);
    model.add(node);
    const listener = new NodeSelectToolMouseListener('node', {} as any);
    const d = diagram();
    let actions: SelectAction[] = [];
    d.root.addEventListener(
      'mouseup',
      (event) => (actions = listener.nonDraggingMouseUp(node, event) as SelectAction[]),
      { once: true },
    );
    pick(d).dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button: 0 }));
    return actions.flatMap((action) => action.selectedElementsIDs);
  }

  it('selects the node under a click on the diagram', () => {
    expect(selectedAfterMouseUp((d) => d.node)).toEqual(['n1']);
  });

  it('selects nothing on a click on the icon of an overlay button', () => {
    expect(selectedAfterMouseUp((d) => d.icon)).toEqual([]);
  });
});
