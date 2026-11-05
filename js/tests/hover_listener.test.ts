/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { describe, expect, it } from 'vitest';

import { HoverFeedbackAction } from 'sprotty-protocol';

import { SModelRootImpl, SNodeImpl, createFeatureSet, isHoverable } from 'sprotty';
import { DOMHelper } from 'sprotty/lib/base/views/dom-helper';

import { ElkLabel, ElkNode } from '../sprotty/sprotty-model';
import { DragAwareHoverMouseListener } from '../tools/draw-aware-mouse-listener';
import { DiagramTool } from '../tools/tool';

// UNIT test (node, no browser): real sprotty model elements, no DOM events.
// HoverFeedbackCommand only applies feedback to elements that `isHoverable`;
// a plain label (no `selectable`) is not, so an action aimed at it is dropped.
function nodeWithLabel() {
  const root = new SModelRootImpl();
  const node = new ElkNode();
  node.id = 'n1';
  node.type = 'node';
  node.features = createFeatureSet(SNodeImpl.DEFAULT_FEATURES); // as the model factory does
  const label = new ElkLabel();
  label.id = 'n1.title';
  label.type = 'label';
  label.text = 'title';
  label.properties = { cssClasses: 'title' };
  root.add(node); // parents are indexed on add: attach to the root first
  node.add(label);
  return { node, label };
}

const listener = new DragAwareHoverMouseListener('node', new DiagramTool());

describe('DragAwareHoverMouseListener target attribution', () => {
  it('attributes hover over a non-hoverable label to its hoverable node', () => {
    const { node, label } = nodeWithLabel();
    expect(isHoverable(label)).toBeFalsy();
    expect(isHoverable(node)).toBe(true);

    const over = listener.mouseOver(label, {} as MouseEvent) as HoverFeedbackAction[];
    expect(over.map((a) => [a.mouseoverElement, a.mouseIsOver])).toEqual([
      ['n1', true],
    ]);

    const out = listener.mouseOut(label, {} as MouseEvent) as HoverFeedbackAction[];
    expect(out.map((a) => [a.mouseoverElement, a.mouseIsOver])).toEqual([
      ['n1', false],
    ]);
  });

  it('keeps hover on a selectable label itself (first-class row)', () => {
    const { label } = nodeWithLabel();
    label.properties = { selectable: true };
    expect(isHoverable(label)).toBe(true);
    const over = listener.mouseOver(label, {} as MouseEvent) as HoverFeedbackAction[];
    expect(over[0].mouseoverElement).toBe('n1.title');
  });

  it('emits nothing when no ancestor is hoverable', () => {
    const root = new SModelRootImpl();
    expect(listener.mouseOver(root, {} as MouseEvent)).toEqual([]);
    expect(listener.mouseOut(root, {} as MouseEvent)).toEqual([]);
  });
});

describe('hover pointer boundaries', () => {
  const dom = (id: string, parentElement: Element | null = null) =>
    ({ id, parentElement }) as Element;
  const boundaryListener = new DragAwareHoverMouseListener(
    'node',
    new DiagramTool(),
    new DOMHelper(),
  );

  it('does not clear between a node and its own non-hoverable label', () => {
    const { node, label } = nodeWithLabel();
    expect(
      boundaryListener.mouseOut(node, {
        relatedTarget: dom(label.id),
      } as unknown as MouseEvent),
    ).toEqual([]);
    expect(
      boundaryListener.mouseOut(label, {
        relatedTarget: dom('', dom(node.id)),
      } as unknown as MouseEvent),
    ).toEqual([]);
  });

  it('leaves directly for another hoverable target without an intermediate clear', () => {
    const { node, label } = nodeWithLabel();
    label.properties = { selectable: true };
    expect(
      boundaryListener.mouseOut(node, {
        relatedTarget: dom(label.id),
      } as unknown as MouseEvent),
    ).toEqual([]);
    const actions = boundaryListener.mouseOver(
      label,
      {} as MouseEvent,
    ) as HoverFeedbackAction[];
    expect(actions.map((a) => [a.mouseoverElement, a.mouseIsOver])).toEqual([
      [label.id, true],
    ]);
  });

  it('still clears when leaving for empty canvas or outside the view', () => {
    const { node } = nodeWithLabel();
    for (const relatedTarget of [null, dom('not-in-model')]) {
      const actions = boundaryListener.mouseOut(node, {
        relatedTarget,
      } as unknown as MouseEvent) as HoverFeedbackAction[];
      expect(actions.map((a) => [a.mouseoverElement, a.mouseIsOver])).toEqual([
        [node.id, false],
      ]);
    }
  });
});
