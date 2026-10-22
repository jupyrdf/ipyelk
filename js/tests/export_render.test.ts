/**
 * @vitest-environment happy-dom
 *
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { HoverFeedbackAction, SelectAction, SetViewportAction } from 'sprotty-protocol';

import {
  ActionDispatcher,
  CommandStack,
  ModelViewer,
  SModelRootImpl,
  TYPES,
} from 'sprotty';

import createContainer from '../sprotty/di-config';
import { JLModelSource } from '../sprotty/diagram-server';
import { exportMarkup } from '../sprotty/export_render';
import { ElkNode } from '../sprotty/json/elkgraph-json';

vi.mock('../tokens', () => ({ ELK_DEBUG: false }));

// A view through the extension's own container (happy-dom): with culling on,
// the live SVG holds only what the camera shows, while an export is the whole
// diagram, the same markup at any camera and with culling on or off, and is
// no render of the view.

const CANVAS = { x: 0, y: 0, width: 800, height: 600 };

/** Ten 30x30 nodes in a row 500 px apart, chained by edges, each with a label. */
const LAYOUT: ElkNode = {
  id: 'root',
  width: 5000,
  height: 100,
  children: Array.from({ length: 10 }, (_, i) => ({
    id: `n${i}`,
    x: 10 + 500 * i,
    y: 10,
    width: 30,
    height: 30,
    labels: [{ id: `n${i}.l`, text: `node ${i}`, x: 0, y: 32, width: 40, height: 14 }],
  })),
  edges: Array.from({ length: 9 }, (_, i) => ({
    id: `e${i}`,
    sources: [`n${i}`],
    targets: [`n${i + 1}`],
    sections: [
      {
        id: `e${i}.s`,
        startPoint: { x: 40 + 500 * i, y: 25 },
        endPoint: { x: 10 + 500 * (i + 1), y: 25 },
      },
    ],
  })),
};

function nextFrame(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

/** The exporter strips the root group's viewport transform: compare as it does. */
function withoutCamera(markup: string): string {
  return markup.replace(/ transform=".*?"/, '');
}

describe('culling and the export', () => {
  let div: HTMLDivElement;
  let container: ReturnType<typeof createContainer>;
  let source: JLModelSource;
  let dispatcher: ActionDispatcher;
  let stack: CommandStack;
  let viewer: ModelViewer;
  let update: ReturnType<typeof vi.spyOn>;
  const boundingRect = HTMLElement.prototype.getBoundingClientRect;

  beforeEach(async () => {
    // happy-dom lays nothing out: give every element the canvas size, as
    // sprotty's `CanvasBoundsInitializer` measures the root after each render
    HTMLElement.prototype.getBoundingClientRect = () =>
      ({ ...CANVAS, top: 0, left: 0, right: 800, bottom: 600 }) as DOMRect;
    div = document.createElement('div');
    div.id = 'c0';
    document.body.appendChild(div);
    container = createContainer('c0', null as any);
    source = container.get<JLModelSource>(TYPES.ModelSource);
    source.factory = container.get(TYPES.IModelFactory);
    dispatcher = container.get<ActionDispatcher>(TYPES.IActionDispatcher);
    stack = container.get<CommandStack>(TYPES.ICommandStack);
    viewer = container.get(ModelViewer);
    update = vi.spyOn(ModelViewer.prototype, 'update');
    source.culling = true;
    source.resize(CANVAS);
    await source.updateLayout(LAYOUT, { library: {} }, 'c0', {});
    await rendered();
  });

  afterEach(() => {
    update.mockRestore();
    HTMLElement.prototype.getBoundingClientRect = boundingRect;
    document.body.replaceChildren();
  });

  /** The model once the command stack has run and rendered what was queued. */
  async function rendered(): Promise<SModelRootImpl> {
    const root = await (stack as unknown as { currentModel: Promise<SModelRootImpl> })
      .currentModel;
    // sprotty's ViewerCache renders at the end of the next frame; a second
    // frame leaves no doubt about the timer order in happy-dom
    await nextFrame();
    await nextFrame();
    return root;
  }

  /** Elements in the view: sprotty's first render replaces the placeholder `div`. */
  function live(selector: string): number {
    return document.getElementById('c0')!.querySelectorAll(selector).length;
  }

  function count(markup: string, cls: string): number {
    return (markup.match(new RegExp(`class="[^"]*\\b${cls}\\b[^"]*"`, 'g')) || [])
      .length;
  }

  async function camera(scroll: { x: number; y: number }, zoom: number) {
    const root = await rendered();
    await dispatcher.dispatch(
      SetViewportAction.create(root.id, { scroll, zoom }, { animate: false }),
    );
    return rendered();
  }

  it('renders the whole diagram when it fits, and only what is on screen zoomed in', async () => {
    // zoomed out so the 5000 px row fits the 800 px canvas: everything is drawn
    await camera({ x: 0, y: 0 }, 0.1);
    expect(live('.elknode')).toBe(10);
    expect(live('.elkedge')).toBe(9);
    // a fresh view opens at 1:1 at the origin: x in [0, 800) shows nodes n0 and
    // n1, and the edges that touch that span (e0 in it, e1 leaving it)
    await camera({ x: 0, y: 0 }, 1);
    expect(live('.elknode')).toBe(2);
    expect(live('.elkedge')).toBe(2);
    expect(live('.elklabel')).toBe(2);
    await camera({ x: 2000, y: 0 }, 1);
    expect(live('.elknode')).toBe(2);
    // zoomed out again, everything is back
    await camera({ x: 0, y: 0 }, 0.1);
    expect(live('.elknode')).toBe(10);
    expect(live('.elkedge')).toBe(9);
  });

  it('exports the whole diagram at any camera, culling on or off', async () => {
    const root = await rendered();
    const full = exportMarkup(container, root);
    expect(full).not.toBeNull();
    expect(count(full!, 'elknode')).toBe(10);
    expect(count(full!, 'elkedge')).toBe(9);
    expect(count(full!, 'elklabel')).toBe(10);

    const zoomed = await camera({ x: 0, y: 0 }, 1);
    expect(live('.elknode')).toBe(2); // the view is culled ...
    const culled = exportMarkup(container, zoomed)!;
    expect(withoutCamera(culled)).toBe(withoutCamera(full!)); // ... the export is not

    source.culling = false;
    const uncut = exportMarkup(container, await camera({ x: 0, y: 0 }, 1))!;
    expect(withoutCamera(uncut)).toBe(withoutCamera(full!));
  });

  it('exports every label, even ones the view drops as too small to read', async () => {
    // 14 px labels at zoom 0.1 are 1.4 px tall: the view leaves them out
    const root = await camera({ x: 0, y: 0 }, 0.1);
    expect(live('.elklabel')).toBe(0);
    expect(count(exportMarkup(container, root)!, 'elklabel')).toBe(10);
  });

  it('is no render of the view, while a selection or a hover is exactly one', async () => {
    const root = await rendered();
    update.mockClear();
    exportMarkup(container, root);
    expect(update).not.toHaveBeenCalled();
    expect(viewer).toBeDefined();

    await dispatcher.dispatch(
      SelectAction.create({ selectedElementsIDs: ['n0'], deselectedElementsIDs: [] }),
    );
    await rendered();
    expect(update).toHaveBeenCalledTimes(1);
    expect(live('.elknode.selected')).toBe(1);

    await dispatcher.dispatch(
      HoverFeedbackAction.create({ mouseoverElement: 'n1', mouseIsOver: true }),
    );
    await rendered();
    expect(update).toHaveBeenCalledTimes(2);
    expect(live('.elknode.mouseover')).toBe(1);
    // the export carries the selection, which the kernel also knows, as before
    expect(count(exportMarkup(container, root)!, 'selected')).toBe(1);
    expect(update).toHaveBeenCalledTimes(2);
  });

  it('attaches no widget container for an export', async () => {
    const root = await rendered();
    const markup = exportMarkup(container, root)!;
    expect(markup.startsWith('<svg')).toBe(true);
    expect(markup).not.toContain('elkcontainer');
    expect(markup).not.toContain('sprotty-overlay');
  });
});
