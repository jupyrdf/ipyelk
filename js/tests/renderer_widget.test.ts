/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { describe, expect, it, vi } from 'vitest';

import { ElkModelRenderer } from '../sprotty/renderer';
import { ElkNode } from '../sprotty/sprotty-model';

vi.mock('../tokens', () => ({ ELK_DEBUG: false }));

function setup() {
  const renderer = Object.create(ElkModelRenderer.prototype) as ElkModelRenderer;
  const manager = {
    get_model: vi.fn(),
    create_view: vi.fn(),
  };
  Object.assign(renderer, { source: { widget_manager: manager }, widgets: {} });
  const node = new ElkNode();
  node.id = 'n';
  node.type = 'node:widget';
  node.properties = { shape: { type: 'node:widget', use: 'closed-id' } };
  return { renderer, manager, node };
}

describe('closed widget shapes', () => {
  it('replaces a prior registration without rejecting when the model closes', async () => {
    const { renderer, manager, node } = setup();
    const live = {};
    manager.get_model.mockResolvedValueOnce(live);
    await renderer.registerJLWidgetNode(undefined, node, true);
    expect(renderer.widgets.n.widget).toBe(live);
    manager.get_model.mockRejectedValueOnce(new Error('widget model not found'));
    await expect(
      renderer.registerJLWidgetNode(undefined, node, true),
    ).resolves.toBeUndefined();
    expect(renderer.widgets.n.widget).toBeUndefined();
    expect(manager.create_view).not.toHaveBeenCalled();
  });

  it('leaves no attached widget when a model disappears before overlay insertion', async () => {
    const { renderer, manager, node } = setup();
    const host = document.createElement('div');
    document.body.append(host);
    manager.get_model.mockRejectedValueOnce(new Error('widget model not found'));
    await expect(
      renderer.renderContent({ elm: host } as any, {
        vnode: undefined,
        node,
        widget: 'closed-id',
        visible: true,
        html: undefined,
      }),
    ).resolves.toBeUndefined();
    expect(host.children).toHaveLength(0);
    expect(manager.create_view).not.toHaveBeenCalled();
    host.remove();
  });
});
