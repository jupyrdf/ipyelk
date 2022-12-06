/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { injectable } from 'inversify';
import {
  Action,
  Bounds,
  CenterAction,
  FitToScreenAction,
  GetViewportAction,
  InitializeCanvasBoundsAction,
  LocalModelSource,
  Match,
  SModelElement,
  SModelElementSchema,
  SModelIndex, // SModelFactory,
  SModelRegistry,
  SModelRoot,
  SModelRootSchema,
  Viewport,
} from 'sprotty';

import type { IWidgetManager } from '@jupyter-widgets/base';

import { ELK_DEBUG } from '../tokens';

import { ElkGraphJsonToSprotty, SSymbolGraphSchema } from './json/elkgraph-to-sprotty';
import { SSymbolModelFactory } from './renderer';
import { ElkNode } from './sprotty-model';

@injectable()
export class JLModelSource extends LocalModelSource {
  elkToSprotty: ElkGraphJsonToSprotty;
  widget_manager: IWidgetManager;
  control_overlay: any;
  selectedNodes: ElkNode[];
  index: SModelIndex<SModelElementSchema>;
  elementRegistry: SModelRegistry;
  factory: SSymbolModelFactory;
  diagramWidget: any;

  async updateLayout(layout, symbols, idPrefix: string) {
    this.elkToSprotty = new ElkGraphJsonToSprotty();
    let sGraph: SSymbolGraphSchema = this.elkToSprotty.transform(
      layout,
      symbols,
      idPrefix
    );
    await this.updateModel(sGraph);
    // TODO this promise resolves before ModelViewer rendering is done. need to hook into postprocessing
  }

  public get root(): SModelRoot {
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
    newRoot: SModelRootSchema,
    update: boolean | Match[],
    cause?: Action,
    index?: SModelIndex<SModelElementSchema>
  ): Promise<void> {
    ELK_DEBUG && console.log('doSubmitModel');
    super.doSubmitModel(newRoot, update, cause, index);
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
    let action = new CenterAction(elementIds, animate, retainZoom);
    this.actionDispatcher.dispatch(action);
  }

  fit(
    elementIds: string[] = [],
    padding?: number,
    maxZoom?: number,
    animate?: boolean
  ) {
    let action = new FitToScreenAction(elementIds, padding, maxZoom, animate);
    this.actionDispatcher.dispatch(action);
  }

  resize(bounds: Bounds) {
    let action = new InitializeCanvasBoundsAction(bounds);
    this.actionDispatcher.dispatch(action);
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
