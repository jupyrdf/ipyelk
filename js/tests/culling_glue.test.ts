/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { describe, expect, it, vi } from 'vitest';

import { HoverFeedbackAction } from 'sprotty-protocol';

import { ELKViewerView } from '../display_widget';

vi.mock('../tokens', () => ({ ELK_DEBUG: false }));

describe('view culling wiring', () => {
  it('applies an opt-in toggle and re-renders the submitted model once', () => {
    let enabled: boolean | undefined = false;
    const view = Object.create(ELKViewerView.prototype) as ELKViewerView;
    Object.assign(view, {
      model: { get: () => enabled },
      source: { culling: false, index: {}, updateModel: vi.fn(async () => {}) },
    });
    view.updateCulling();
    expect(view.source.updateModel).not.toHaveBeenCalled();
    enabled = true;
    view.updateCulling();
    expect(view.source.culling).toBe(true);
    expect(view.source.updateModel).toHaveBeenCalledTimes(1);
    view.updateCulling();
    expect(view.source.updateModel).toHaveBeenCalledTimes(1);
    enabled = false;
    view.updateCulling();
    expect(view.source.culling).toBe(false);
    expect(view.source.updateModel).toHaveBeenCalledTimes(2);
    enabled = undefined;
    view.updateCulling();
    expect(view.source.culling).toBe(false);
    expect(view.source.updateModel).toHaveBeenCalledTimes(2);
  });

  it('defers rendering before the first layout', () => {
    const view = Object.create(ELKViewerView.prototype) as ELKViewerView;
    Object.assign(view, {
      model: { get: () => true },
      source: { culling: false, updateModel: vi.fn(async () => {}) },
    });
    view.updateCulling();
    expect(view.source.culling).toBe(true);
    expect(view.source.updateModel).not.toHaveBeenCalled();
  });

  it('identifies pointer feedback as hover', () => {
    const view = Object.create(ELKViewerView.prototype) as ELKViewerView;
    const emit = vi.fn();
    const hover = { get: () => null, set: vi.fn(), save_changes: vi.fn() };
    Object.assign(view, { model: { get: () => hover, diagramUpdated: { emit } } });
    view.handle(
      HoverFeedbackAction.create({ mouseoverElement: 'n1', mouseIsOver: true }),
    );
    expect(hover.set).toHaveBeenCalledExactlyOnceWith('hovered_id', 'n1');
    expect(hover.save_changes).toHaveBeenCalledOnce();
    expect(emit).toHaveBeenCalledExactlyOnceWith('hover');
  });

  it('identifies replayed hover updates as hover, not selection', async () => {
    const view = Object.create(ELKViewerView.prototype) as ELKViewerView;
    const emit = vi.fn();
    const hover = { get: () => 'n1', previous: () => null };
    Object.assign(view, {
      model: { get: () => hover, diagramUpdated: { emit } },
      actionDispatcher: { dispatchAll: vi.fn(async () => {}) },
    });
    await view.updateHover();
    expect(view.actionDispatcher.dispatchAll).toHaveBeenCalledOnce();
    expect(emit).toHaveBeenCalledExactlyOnceWith('hover');
  });
});
