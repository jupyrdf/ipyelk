/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */

/** @jsx svg */
import { injectable } from 'inversify';

import {
  Action,
  Bounds,
  CenterAction,
  FitToScreenAction,
  GetViewportAction,
  SModelElement,
  SModelIndex, // SModelFactory,
  SModelRoot,
  SetViewportAction,
  Viewport,
} from 'sprotty-protocol';

import {
  InitializeCanvasBoundsAction,
  LocalModelSource,
  Match,
  SModelRegistry,
  SModelRootImpl,
} from 'sprotty';

import type { IWidgetManager, WidgetModel } from '@jupyter-widgets/base';

import { ELK_DEBUG } from '../tokens';

import {
  ElkGraphJsonToSprotty,
  PainterStyles,
  SSymbolGraph,
} from './json/elkgraph-to-sprotty';
import { SSymbolModelFactory } from './renderer';

@injectable()
export class JLModelSource extends LocalModelSource {
  elkToSprotty: ElkGraphJsonToSprotty;
  widget_manager: IWidgetManager;
  // The kernel's `Viewer.control_overlay`, or null when opted out.
  control_overlay: WidgetModel | null;
  /**
   * Ids of selected submitted schema elements. The renderer resolves each id
   * to its rendered instance with `getById`; retaining only this structural
   * contract prevents schema and implementation objects being mixed.
   */
  selectedNodes: Array<Pick<SModelElement, 'id'>>;
  index: SModelIndex;
  elementRegistry: SModelRegistry;
  factory: SSymbolModelFactory;
  diagramWidget: any;
  /**
   * Whether this view's renders skip elements outside its canvas: the view's
   * copy of the kernel's `Viewer.cull_offscreen` (#170).
   *
   * The node, label and edge views skip an element whose absolute bounds (an
   * edge's route) miss the canvas, once the canvas size is known and never for
   * the hidden render. Zoomed into a large diagram that saves most of a
   * render and all of the style and layout work a change costs; where the
   * whole diagram is on screen it adds a bounds walk per element, 5-8% of a
   * render (`scripts/bench_render.py`). A node is skipped whole, with its
   * ports and labels, even when an outside-placed label of it would still
   * touch the canvas. The export does not read the live SVG, so it is whole
   * either way (`export_render.ts`).
   */
  culling: boolean = false;

  async updateLayout(layout, symbols, idPrefix: string, styles: PainterStyles = {}) {
    this.elkToSprotty = new ElkGraphJsonToSprotty();
    let sGraph: SSymbolGraph = this.elkToSprotty.transform(
      layout,
      symbols,
      idPrefix,
      styles,
    );
    await this.updateModel(sGraph);
    // TODO(#43): this promise resolves before ModelViewer rendering is done; hook into
    // postprocessing
  }

  public get root(): SModelRootImpl {
    return this.factory.root;
  }

  /*
   * Helper method to return the appropriate sprotty model element in the current
   * graph based on id
   */
  getById(id: string): SModelElement {
    return this.factory.root.index.getById(id);
  }

  /**
   * Submit the given model with an `UpdateModelAction` or a `SetModelAction` depending on the
   * `update` argument. If available, the model layout engine is invoked first.
   */
  protected async doSubmitModel(
    newRoot: SModelRoot,
    update: boolean | Match[],
    cause?: Action,
    index?: SModelIndex,
  ): Promise<void> {
    ELK_DEBUG && console.log('doSubmitModel');
    await super.doSubmitModel(newRoot, update, cause, index);
    if (!index) {
      index = new SModelIndex();
      index.add(this.currentRoot);
    }
    this.index = index;
  }

  element(): HTMLElement {
    return document.getElementById(this.viewerOptions.baseDiv);
  }

  center(elementIds: string[] = [], animate = true, retainZoom = false) {
    let action = CenterAction.create(elementIds, {
      animate: animate,
      retainZoom: retainZoom,
    });
    this.actionDispatcher.dispatch(action);
  }

  fit(
    elementIds: string[] = [],
    padding?: number,
    maxZoom?: number,
    animate?: boolean,
  ) {
    let action = FitToScreenAction.create(elementIds, {
      padding: padding,
      maxZoom: maxZoom,
      animate: animate,
    });
    this.actionDispatcher.dispatch(action);
  }

  resize(bounds: Bounds) {
    let action = InitializeCanvasBoundsAction.create(bounds);
    this.actionDispatcher.dispatch(action);
  }

  /**
   * Move the camera: `null` origin/zoom keep the current value.
   */
  async setViewport(
    origin: [number, number] | null,
    zoom: number | null,
    animate: boolean,
  ): Promise<void> {
    const current = await this.getViewport();
    const next: Viewport = {
      scroll: origin == null ? current.scroll : { x: origin[0], y: origin[1] },
      zoom: zoom == null ? current.zoom : zoom,
    };
    await this.actionDispatcher.dispatch(
      SetViewportAction.create(this.root.id, next, { animate }),
    );
  }

  /**
   * Get the current viewport from the model.
   */
  async getViewport(): Promise<Viewport & { canvasBounds: Bounds }> {
    const res = await this.actionDispatcher.request(GetViewportAction.create());
    return {
      scroll: res.viewport.scroll,
      zoom: res.viewport.zoom,
      canvasBounds: res.canvasBounds,
    };
  }
}
