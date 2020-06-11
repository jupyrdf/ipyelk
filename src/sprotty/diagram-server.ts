import { injectable } from 'inversify';
import {
  CenterAction,
  FitToScreenAction,
  LocalModelSource,
  Viewport,
  Bounds,
  GetViewportAction
} from 'sprotty';
import { ElkGraphJsonToSprotty } from './json/elkgraph-to-sprotty';

@injectable()
export class JLModelSource extends LocalModelSource {
  async updateLayout(layout) {
    let sGraph = new ElkGraphJsonToSprotty().transform(layout);
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
