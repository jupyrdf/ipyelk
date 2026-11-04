/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ELKExporterModel } from '../exporter';

vi.mock('../display_widget', () => ({
  ELKViewerView: class {},
  ELKViewerModel: class {},
}));
vi.mock('../tokens', () => ({ ELK_DEBUG: false }));

describe('export scheduling', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  function exporter(enabled = true) {
    const model = Object.create(ELKExporterModel.prototype) as ELKExporterModel;
    Object.assign(model, { get: () => enabled, _on_layout_updated: vi.fn() });
    return model;
  }

  it('ignores hover without delaying a pending selection export', () => {
    const model = exporter();
    model._schedule_update(undefined, 'hover');
    vi.advanceTimersByTime(1000);
    expect(model._on_layout_updated).not.toHaveBeenCalled();
    model._schedule_update(undefined, 'selection');
    vi.advanceTimersByTime(500);
    model._schedule_update(undefined, 'hover');
    vi.advanceTimersByTime(500);
    expect(model._on_layout_updated).toHaveBeenCalledOnce();
  });

  it('debounces layout and selection updates, including legacy unspecified reasons', () => {
    const model = exporter();
    model._schedule_update(undefined, 'layout');
    vi.advanceTimersByTime(500);
    model._schedule_update(undefined, 'selection');
    vi.advanceTimersByTime(999);
    expect(model._on_layout_updated).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(model._on_layout_updated).toHaveBeenCalledOnce();
    model._schedule_update();
    vi.advanceTimersByTime(1000);
    expect(model._on_layout_updated).toHaveBeenCalledTimes(2);
  });

  it('does not schedule while disabled', () => {
    const model = exporter(false);
    model._schedule_update(undefined, 'layout');
    vi.advanceTimersByTime(1000);
    expect(model._on_layout_updated).not.toHaveBeenCalled();
  });
});
