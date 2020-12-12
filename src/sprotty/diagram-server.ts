/**
 * Copyright (c) 2020 Dane Freeman.
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
  SGraphSchema,
  Viewport,
} from 'sprotty';
import { ElkGraphJsonToSprotty } from './json/elkgraph-to-sprotty';

@injectable()
export class JLModelSource extends LocalModelSource {
  elkToSprotty: ElkGraphJsonToSprotty;

  async updateLayout(layout, defs, idPrefix:string) {
    this.elkToSprotty = new ElkGraphJsonToSprotty()
    let sGraph:SGraphSchema = this.elkToSprotty.transform(layout, defs, idPrefix);
    console.warn("update layout");
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
    // console.log("get viewpoint")
    return {
      scroll: res.viewport.scroll,
      zoom: res.viewport.zoom,
      canvasBounds: res.canvasBounds
    };
  }
}
