/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { injectable } from 'inversify';
import {
  Bounds,
  CenterAction,
  FitToScreenAction,
  GetViewportAction,
  InitializeCanvasBoundsAction,
  LocalModelSource,
  Viewport
} from 'sprotty';
import { ElkGraphJsonToSprotty, SDefGraphSchema } from './json/elkgraph-to-sprotty';
import { ManagerBase } from '@jupyter-widgets/base';
import { Widget } from '@phosphor/widgets';
// import { WidgetManager } from '@jupyter-widgets/jupyterlab-manager';
@injectable()
export class JLModelSource extends LocalModelSource {
  elkToSprotty: ElkGraphJsonToSprotty;
  widget_manager: ManagerBase<Widget>;
  // widget_manager: WidgetManager;

  async updateLayout(layout, defs, idPrefix: string) {
    this.elkToSprotty = new ElkGraphJsonToSprotty();
    let sGraph: SDefGraphSchema = this.elkToSprotty.transform(layout, defs, idPrefix);
    await this.updateModel(sGraph);
    // TODO this promise resolves before ModelViewer rendering is done. need to hook into postprocessing
  }

  async getSelected() {
    let ids = [];
    let selected = await this.getSelection();
    selected.forEach((node, i) => {
      ids.push(node.id);
    });
    return ids;
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
      canvasBounds: res.canvasBounds
    };
  }
}
