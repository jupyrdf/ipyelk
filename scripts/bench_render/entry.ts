/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 *
 * The in-page half of `scripts/bench_render.py`.
 *
 * Renders laid-out graphs (fixtures from `bench_render_fixtures.py`) with the
 * extension's own sprotty container -- the same DI modules, views, model
 * source and update command a `SprottyViewer` view uses -- and times what a
 * view does on each kind of update, with culling off or on, at a chosen
 * viewport. A driver calls `window.elkBench.runAll(config)` over WebDriver or
 * Playwright, or the page runs itself when opened with `?auto` and stores the
 * result in `window.elkBenchResult`.
 */
import 'reflect-metadata';

import {
  Action,
  Bounds,
  FitToScreenAction,
  HoverFeedbackAction,
  SelectAction,
  SetViewportAction,
  Viewport,
} from 'sprotty-protocol';

import {
  ActionDispatcher,
  CommandStack,
  ModelViewer,
  SModelRootImpl,
  TYPES,
  isViewport,
} from 'sprotty';

import createContainer from '../../js/sprotty/di-config';
import { JLModelSource } from '../../js/sprotty/diagram-server';
import { contentBounds } from '../../js/sprotty/export_util';
import { ElkNode } from '../../js/sprotty/json/elkgraph-json';
import { IElkSymbols } from '../../js/sprotty/json/symbols';
import '../../style/index.css';

/** The sprotty div's size: the canvas every fit and zoom is relative to. */
export const CANVAS = { width: 1200, height: 800 };
const ROOT_ID = 'bench-root';

export const OPS = ['render', 'select', 'hover', 'pan', 'relayout'] as const;
export type Op = (typeof OPS)[number];

interface Fixture {
  shape: string;
  n: number;
  elements: Record<string, number>;
  layout: ElkNode;
  symbols: IElkSymbols;
}

/** One timed update, in milliseconds. */
export interface Sample {
  op: Op | 'first';
  /** from dispatch until the command stack resolved: the command itself, an
   * animation's every frame included; a plain command's render is deferred
   * to the next animation frame by sprotty's `ViewerCache`, so for one it is
   * the command alone */
  dispatch: number;
  /** time inside `ModelViewer.update`: view functions, culling, snabbdom patch */
  render: number;
  /** how many `ModelViewer.update` calls the operation ran (animations run many) */
  updates: number;
  /** when each of those renders ended, in ms after the dispatch began */
  renderEnds: number[];
  /** a forced `getBBox()` on the diagram group once the render has run: the
   * style and SVG geometry work the DOM change left pending */
  layout: number;
  /** from dispatch to the animation frame after the one that rendered: when a
   * painted frame could first show the change, rounded up to the display's
   * refresh interval */
  frame: number;
}

export interface DomCounts {
  nodes: number;
  edges: number;
  labels: number;
  ports: number;
  /** `svg.outerHTML.length`: what the exporter would serialize */
  svgChars: number;
}

export type ViewportSpec = 'fit' | { zoom: number };

export interface RunConfig {
  culling: boolean;
  viewport: ViewportSpec;
  ops: Op[];
  repeat: number;
}

export interface RunResult {
  key: string;
  culling: boolean;
  viewport: string;
  camera: Viewport;
  samples: Sample[];
  dom: DomCounts;
}

export interface CaseResult {
  case: string;
  shape: string;
  n: number;
  elements: Record<string, number>;
  first: Sample;
  dom_full: DomCounts;
  /** `cull/fit`, `nocull/zoom1`, ...: samples of every kept round, appended */
  runs: Record<string, RunResult>;
  log: string[];
}

export interface ScheduleConfig {
  /** fixture urls, relative to the page */
  fixtures: string[];
  ops: Op[];
  /** rounds kept; one more runs first as a warm-up and is dropped */
  rounds: number;
  /** repeats of every op per round */
  repeat: number;
  /** the zoomed viewports, each centered on the content */
  zooms: number[];
}

export interface ScheduleResult {
  userAgent: string;
  canvas: typeof CANVAS;
  config: ScheduleConfig;
  cases: CaseResult[];
}

/** `ModelViewer.update` calls since the last `measure` began: [duration, end time]. */
const renders: [number, number][] = [];
const originalUpdate = ModelViewer.prototype.update;
ModelViewer.prototype.update = function (
  this: ModelViewer,
  model: SModelRootImpl,
  cause?: Action,
): void {
  const t0 = performance.now();
  originalUpdate.call(this, model, cause);
  const t1 = performance.now();
  renders.push([t1 - t0, t1]);
};

function nextFrame(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

function diagramGroup(): SVGGElement | null {
  return document.querySelector(`#${ROOT_ID} svg.sprotty-graph > g`);
}

function count(selector: string): number {
  return document.querySelectorAll(`#${ROOT_ID} ${selector}`).length;
}

function domCounts(): DomCounts {
  const svg = document.querySelector(`#${ROOT_ID} svg.sprotty-graph`);
  return {
    nodes: count('.elknode'),
    edges: count('.elkedge'),
    labels: count('.elklabel'),
    ports: count('.elkport'),
    svgChars: svg?.outerHTML.length ?? 0,
  };
}

function viewportKey(viewport: ViewportSpec): string {
  return viewport === 'fit' ? 'fit' : `zoom${viewport.zoom}`;
}

export class Bench {
  private source: JLModelSource;
  private dispatcher: ActionDispatcher;
  private stack: CommandStack;
  private viewer: ModelViewer;
  private fixture: Fixture;
  /** progress lines, for a driver to poll */
  readonly log: string[] = [];

  /** Every case at every culling x viewport combination, interleaved by round. */
  async runAll(config: ScheduleConfig): Promise<ScheduleResult> {
    const cases: CaseResult[] = [];
    for (const url of config.fixtures) {
      cases.push(await this.runCase(url, config));
    }
    this.dispose();
    return { userAgent: navigator.userAgent, canvas: CANVAS, config, cases };
  }

  async runCase(url: string, config: ScheduleConfig): Promise<CaseResult> {
    const loaded = await this.load(url);
    const { fixture } = loaded;
    const result: CaseResult = {
      case: `${fixture.shape}:${fixture.n}`,
      shape: fixture.shape,
      n: fixture.n,
      elements: fixture.elements,
      first: loaded.first,
      dom_full: loaded.dom,
      runs: {},
      log: [],
    };
    const viewports: ViewportSpec[] = [
      'fit',
      ...config.zooms.map((zoom) => ({ zoom })),
    ];
    for (let round = 0; round <= config.rounds; round++) {
      for (const culling of [false, true]) {
        for (const viewport of viewports) {
          const t0 = performance.now();
          const run = await this.run({
            culling,
            viewport,
            ops: config.ops,
            repeat: config.repeat,
          });
          const line =
            `${result.case} round ${round} ${run.key}: ${run.samples.length} samples` +
            ` in ${((performance.now() - t0) / 1000).toFixed(1)} s`;
          this.log.push(line);
          result.log.push(line);
          if (round === 0) {
            continue; // the warm-up round
          }
          const kept = result.runs[run.key];
          if (kept) {
            kept.samples.push(...run.samples);
          } else {
            result.runs[run.key] = run;
          }
        }
      }
    }
    return result;
  }

  async load(
    url: string,
  ): Promise<{ fixture: Fixture; first: Sample; dom: DomCounts }> {
    this.dispose();
    const fixture: Fixture = await (await fetch(url)).json();
    this.fixture = fixture;
    const host = document.getElementById('host')!;
    const div = document.createElement('div');
    div.id = ROOT_ID;
    host.appendChild(div);

    const container = createContainer(ROOT_ID, null as any);
    this.source = container.get<JLModelSource>(TYPES.ModelSource);
    this.source.factory = container.get(TYPES.IModelFactory);
    this.dispatcher = container.get<ActionDispatcher>(TYPES.IActionDispatcher);
    this.stack = container.get<CommandStack>(TYPES.ICommandStack);
    this.viewer = container.get(ModelViewer);
    this.source.resize({ x: 0, y: 0, ...CANVAS });

    const first = await this.measure('first', () => this.relayout());
    return { fixture, first, dom: domCounts() };
  }

  dispose(): void {
    document.getElementById(ROOT_ID)?.remove();
  }

  async run(config: RunConfig): Promise<RunResult> {
    this.source.culling = config.culling;
    await this.select([]); // a fit frames the selection when there is one
    await this.setViewport(config.viewport);
    // the culling flag is read while rendering: settle the DOM on the new
    // flag and camera before anything is timed
    await this.render();
    await nextFrame();
    await nextFrame();

    const samples: Sample[] = [];
    const nodeIds = this.nodeIds();
    for (let i = 0; i < config.repeat; i++) {
      for (const op of config.ops) {
        switch (op) {
          case 'render':
            samples.push(await this.measure(op, () => this.render()));
            break;
          case 'relayout':
            samples.push(await this.measure(op, () => this.relayout()));
            break;
          case 'select':
            samples.push(
              await this.measure(op, () => this.select([nodeIds[i % nodeIds.length]])),
            );
            break;
          case 'hover': {
            const id = nodeIds[(i + 1) % nodeIds.length];
            for (const mouseIsOver of [true, false]) {
              samples.push(
                await this.measure(op, () =>
                  this.dispatcher.dispatch(
                    HoverFeedbackAction.create({ mouseoverElement: id, mouseIsOver }),
                  ),
                ),
              );
            }
            break;
          }
          case 'pan':
            // there and back by a tenth of the canvas, so the camera stays put
            for (const dx of [CANVAS.width / 10, -CANVAS.width / 10]) {
              samples.push(await this.measure(op, () => this.panBy(dx)));
            }
            break;
          default:
            throw new Error(`unknown op ${op}`);
        }
      }
    }
    return {
      key: `${config.culling ? 'cull' : 'nocull'}/${viewportKey(config.viewport)}`,
      culling: config.culling,
      viewport: viewportKey(config.viewport),
      camera: await this.viewport(),
      samples,
      dom: domCounts(),
    };
  }

  /** The top-level nodes of the layout: what the fit frames and the ops pick from. */
  private nodeIds(): string[] {
    return (this.fixture.layout.children || []).map((node) => node.id);
  }

  private selected: string[] = [];

  private async select(ids: string[]): Promise<void> {
    await this.dispatcher.dispatch(
      SelectAction.create({
        selectedElementsIDs: ids,
        deselectedElementsIDs: this.selected.filter((id) => !ids.includes(id)),
      }),
    );
    this.selected = ids;
  }

  /** What a kernel refresh does: transform, build the model, submit, animate. */
  private relayout(): Promise<void> {
    return this.source.updateLayout(
      this.fixture.layout,
      this.fixture.symbols,
      'bench',
      {},
    );
  }

  /** One forced re-render of the current model, outside the command stack. */
  private async render(): Promise<void> {
    this.viewer.update(await this.root());
  }

  /** The model once every queued command has run and rendered. */
  private root(): Promise<SModelRootImpl> {
    // protected on `CommandStack`; the promise chain is the point here
    return (this.stack as unknown as { currentModel: Promise<SModelRootImpl> })
      .currentModel;
  }

  private async viewport(): Promise<Viewport> {
    const root = await this.root();
    if (isViewport(root)) {
      return { scroll: { ...root.scroll }, zoom: root.zoom };
    }
    throw new Error('the root is not a viewport');
  }

  private async setViewport(target: ViewportSpec): Promise<void> {
    const root = await this.root();
    if (target === 'fit') {
      // name every node, as `display_widget.ts` does: with no ids sprotty
      // frames the selection instead when there is one
      await this.dispatcher.dispatch(
        FitToScreenAction.create(this.nodeIds(), { padding: 0, animate: false }),
      );
      return;
    }
    const content: Bounds = contentBounds(root);
    const zoom = target.zoom;
    const centre = Bounds.center(content);
    await this.dispatcher.dispatch(
      SetViewportAction.create(
        root.id,
        {
          scroll: {
            x: centre.x - CANVAS.width / 2 / zoom,
            y: centre.y - CANVAS.height / 2 / zoom,
          },
          zoom,
        },
        { animate: false },
      ),
    );
  }

  private async panBy(dx: number): Promise<void> {
    const root = await this.root();
    const { scroll, zoom } = await this.viewport();
    await this.dispatcher.dispatch(
      SetViewportAction.create(
        root.id,
        { scroll: { x: scroll.x + dx / zoom, y: scroll.y }, zoom },
        { animate: false },
      ),
    );
  }

  private async measure(
    op: Sample['op'],
    action: () => Promise<unknown>,
  ): Promise<Sample> {
    renders.length = 0;
    const t0 = performance.now();
    await action();
    await this.root();
    const dispatched = performance.now();
    // sprotty's `ViewerCache` coalesces a command's render onto the next
    // animation frame, so the dispatch resolves before the DOM changes (#43,
    // #161): the render has run once this frame callback, queued after the
    // cache's, gets its turn
    await nextFrame();
    const rendered = performance.now();
    diagramGroup()?.getBBox();
    const laidOut = performance.now();
    await nextFrame();
    const framed = performance.now();
    return {
      op,
      dispatch: dispatched - t0,
      render: renders.reduce((sum, [ms]) => sum + ms, 0),
      updates: renders.length,
      renderEnds: renders.map(([, end]) => end - t0),
      layout: laidOut - rendered,
      frame: framed - t0,
    };
  }
}

declare global {
  interface Window {
    elkBench: Bench;
    elkBenchResult?: ScheduleResult;
    elkBenchError?: string;
  }
}

/** `?auto&fixtures=a.json,b.json&rounds=5&repeat=5&zooms=1,0.25&ops=select,hover` */
function configFromUrl(params: URLSearchParams): ScheduleConfig {
  const list = (key: string) => (params.get(key) || '').split(',').filter(Boolean);
  const num = (key: string, fallback: number) => Number(params.get(key) ?? fallback);
  const ops = list('ops') as Op[];
  const zooms = list('zooms').map(Number);
  return {
    fixtures: list('fixtures'),
    ops: ops.length ? ops : [...OPS],
    rounds: num('rounds', 5),
    repeat: num('repeat', 5),
    zooms: zooms.length ? zooms : [1],
  };
}

window.elkBench = new Bench();

const params = new URLSearchParams(window.location.search);
if (params.has('auto')) {
  window.elkBench.runAll(configFromUrl(params)).then(
    (result) => {
      window.elkBenchResult = result;
      document.getElementById('result')!.textContent = JSON.stringify(result);
    },
    (err) => {
      window.elkBenchError = String(err?.stack || err);
    },
  );
}
