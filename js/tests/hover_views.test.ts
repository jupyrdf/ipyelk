/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import * as Backbone from 'backbone';
import 'reflect-metadata';
import { describe, expect, it } from 'vitest';

import { Action, HoverFeedbackAction } from 'sprotty-protocol';

import { ActionDispatcher, InitializeCanvasBoundsAction } from 'sprotty';

import { ELKViewerView } from '../display_widget';

// UNIT test (happy-dom): two `ELKViewerView`s of ONE model, as `display(diagram)`
// twice (or a linked output view) makes them, each with a real sprotty
// `ActionDispatcher`. Only the hover path is wired: the view's own `handle` and
// `updateHover`, a shared Backbone hover tool, and no DOM, container or kernel.

const enter = (id: string) =>
  HoverFeedbackAction.create({ mouseoverElement: id, mouseIsOver: true });
const leave = (id: string) =>
  HoverFeedbackAction.create({ mouseoverElement: id, mouseIsOver: false });

// a feedback loop never yields to the event loop: past this many writes the
// views stop handling actions, so the test fails instead of hanging
const WRITE_CAP = 200;

/** A macrotask: every microtask queued before it has run. */
const nextTask = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

function sharedHover() {
  const hover = new Backbone.Model({ hovered_id: null });
  const written: (string | null)[] = [];
  Object.assign(hover, {
    save_changes: () => written.push(hover.get('hovered_id')),
  });
  return { hover, written, halted: () => written.length >= WRITE_CAP };
}

function viewOf({ hover, halted }: ReturnType<typeof sharedHover>) {
  const view = Object.create(ELKViewerView.prototype) as ELKViewerView;
  const hoverHandler = {
    handle: (action: Action) => (halted() ? undefined : view.handle(action)),
  };
  const otherHandler = { handle: (): void => undefined };
  const dispatcher = new ActionDispatcher();
  Object.assign(dispatcher, {
    initialized: Promise.resolve(),
    actionHandlerRegistry: {
      get: (kind: string) =>
        kind === HoverFeedbackAction.KIND ? [hoverHandler] : [otherHandler],
    },
    diagramLocker: { isAllowed: () => true },
    logger: { log() {}, warn() {}, error() {} },
  });
  Object.assign(view, {
    model: {
      get: (key: string) => (key === 'hover' ? hover : null),
      diagramUpdated: { emit() {} },
    },
    actionDispatcher: dispatcher,
  });
  view.updateHoverTool();
  return dispatcher;
}

/** The pointer in one view: sprotty's mouse tool dispatches one action per event. */
async function mouse(dispatcher: ActionDispatcher, ...actions: Action[]) {
  for (const action of actions) {
    dispatcher.dispatch(action);
    await nextTask();
  }
}

describe('two views of one diagram, on hover feedback', () => {
  it('settle after hovers in both views', async () => {
    const shared = sharedHover();
    const [a, b] = [viewOf(shared), viewOf(shared)];

    await mouse(a, enter('n1'), leave('n1'), enter('n2'), leave('n2'));
    await mouse(b, enter('n3'), leave('n3'), enter('n1'));

    expect(shared.written).toEqual(['n1', null, 'n2', null, 'n3', null, 'n1']);
    expect(shared.hover.get('hovered_id')).toBe('n1');
  });

  it('settle when hovers land in one tick, one in each view', async () => {
    const shared = sharedHover();
    const [a, b] = [viewOf(shared), viewOf(shared)];

    a.dispatch(enter('n1'));
    b.dispatch(enter('n2'));
    await nextTask();

    expect(shared.written.length).toBeLessThanOrEqual(10);
    expect(shared.written).toEqual(['n1', 'n2']);
    expect(shared.hover.get('hovered_id')).toBe('n2');
  });

  it("settle when a blocked view replays the other view's hovers late", async () => {
    const shared = sharedHover();
    const [a, b] = [viewOf(shared), viewOf(shared)];
    // as SetModelCommand does until the view has canvas bounds (e.g. while it
    // is hidden): B postpones every action, its hover replays included
    Object.assign(b, {
      blockUntil: (action: Action) => action.kind === InitializeCanvasBoundsAction.KIND,
    });

    await mouse(a, enter('n1'), leave('n1'), enter('n2'));
    expect(shared.written).toEqual(['n1', null, 'n2']);

    // B is shown: its postponed replays of n1, then n2, all land at once
    b.dispatch(
      InitializeCanvasBoundsAction.create({ x: 0, y: 0, width: 100, height: 100 }),
    );
    await nextTask();

    expect(shared.written.length).toBeLessThanOrEqual(10);
    expect(shared.written).toEqual(['n1', null, 'n2']);
    expect(shared.hover.get('hovered_id')).toBe('n2');
  });
});
