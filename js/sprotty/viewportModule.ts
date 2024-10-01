/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { ContainerModule, inject } from 'inversify';

import { Action, Point, SetViewportAction, Viewport } from 'sprotty-protocol';
import { Bounds, CenterAction, Dimension, FitToScreenAction } from 'sprotty-protocol';

import {
  // FitToScreenCommand,
  BoundsAwareViewportCommand, // CenterCommand,
  CenterKeyboardListener,
  GetViewportCommand,
  SModelElementImpl, // GetViewportAction,
  SModelRootImpl,
  SRoutingHandleImpl,
  ScrollMouseListener,
  SetViewportCommand,
  TYPES,
  ZoomMouseListener,
  configureCommand,
  findParentByFeature,
  isMoveable,
  isViewport,
} from 'sprotty';

import { JLModelSource } from './diagram-server';

class ModScrollMouseListener extends ScrollMouseListener {
  /*
    Made this modified class for the scoll mouse listener to help with the inital skip on a scroll event but unable to pin down the error
    */

  constructor(@inject(TYPES.ModelSource) protected model_source: JLModelSource) {
    super();
  }

  mouseDown(target: SModelElementImpl, event: MouseEvent): Action[] {
    const moveable = findParentByFeature(target, isMoveable);
    if (moveable == null && !(target instanceof SRoutingHandleImpl)) {
      if (target.type == 'node:widget') {
        // disable scrolling if mouse down on a widget node.
        this.lastScrollPosition = undefined;
      } else {
        const viewport = findParentByFeature(target, isViewport);
        if (viewport) {
          this.lastScrollPosition = {
            x: event.pageX,
            y: event.pageY,
          };
        } else {
          this.lastScrollPosition = undefined;
        }
      }
    }
    return [];
  }

  mouseMove(target: SModelElementImpl, event: MouseEvent): Action[] {
    if (event.buttons === 0) this.mouseUp(target, event);
    else if (this.lastScrollPosition) {
      const viewport = findParentByFeature(target, isViewport);

      if (viewport) {
        const dx = (event.pageX - this.lastScrollPosition.x) / viewport.zoom;
        const dy = (event.pageY - this.lastScrollPosition.y) / viewport.zoom;
        // const windowScroll = this.model_source.element().getBoundingClientRect()
        const newViewport: Viewport = {
          scroll: {
            x: viewport.scroll.x - dx,
            y: viewport.scroll.y - dy,
          },
          zoom: viewport.zoom,
        };
        this.lastScrollPosition = { x: event.pageX, y: event.pageY };
        return [SetViewportAction.create(viewport.id, newViewport, { animate: false })];
      }
    }
    return [];
  }
}

class ModZoomMouseListener extends ZoomMouseListener {
  /* Modified Zoom Muse Listener to use the base element bounding rectangle for referencing zoom events
   */
  constructor(@inject(TYPES.ModelSource) protected model_source: JLModelSource) {
    super();
  }

  protected getViewportOffset(root: SModelRootImpl, event: WheelEvent): Point {
    const windowScroll = this.model_source.element().getBoundingClientRect();
    const offset = {
      x: event.clientX - windowScroll.left,
      y: event.clientY - windowScroll.top,
    };
    return offset;
  }
}

export class CenterCommand extends BoundsAwareViewportCommand {
  static readonly KIND = CenterAction.KIND;

  constructor(@inject(TYPES.Action) protected action: CenterAction) {
    super(action.animate);
  }

  getElementIds() {
    return this.action.elementIds;
  }

  getNewViewport(bounds: Bounds, model: SModelRootImpl): Viewport | undefined {
    if (!Dimension.isValid(model.canvasBounds)) {
      return void 0;
    }
    let zoom = 1;
    if (this.action.retainZoom && isViewport(model)) {
      zoom = model.zoom;
    } else if (this.action.zoomScale) {
      zoom = this.action.zoomScale;
    }
    const c = Bounds.center(bounds);
    const x = c.x - (0.5 * model.canvasBounds.width) / zoom;
    const y = c.y - (0.5 * model.canvasBounds.height) / zoom;
    return {
      scroll: {
        x: x ? x : 0,
        y: y ? y : 0,
      },
      zoom: zoom,
    };
  }
}

export class FitToScreenCommand extends BoundsAwareViewportCommand {
  static readonly KIND = FitToScreenAction.KIND;

  constructor(@inject(TYPES.Action) protected readonly action: FitToScreenAction) {
    super(action.animate);
  }

  getElementIds() {
    return this.action.elementIds;
  }

  getNewViewport(bounds: Bounds, model: SModelRootImpl): Viewport | undefined {
    if (!Dimension.isValid(model.canvasBounds)) {
      return void 0;
    }
    const c = Bounds.center(bounds);
    const delta = this.action.padding == null ? 0 : 2 * this.action.padding;
    let zoom = Math.min(
      model.canvasBounds.width / (bounds.width + delta),
      model.canvasBounds.height / (bounds.height + delta),
    );
    if (this.action.maxZoom != null) zoom = Math.min(zoom, this.action.maxZoom);
    if (zoom === Infinity) {
      zoom = 1;
    }
    const x = c.x - (0.5 * model.canvasBounds.width) / zoom;
    const y = c.y - (0.5 * model.canvasBounds.height) / zoom;
    return {
      scroll: {
        x: x ? x : 0,
        y: y ? y : 0,
      },
      zoom: zoom,
    };
  }
}

const viewportModule = new ContainerModule((bind, _unbind, isBound) => {
  configureCommand({ bind, isBound }, CenterCommand);
  configureCommand({ bind, isBound }, FitToScreenCommand);
  configureCommand({ bind, isBound }, SetViewportCommand);
  configureCommand({ bind, isBound }, GetViewportCommand);
  bind(TYPES.KeyListener).to(CenterKeyboardListener);
  bind(TYPES.MouseListener).to(ModScrollMouseListener);
  bind(TYPES.MouseListener).to(ModZoomMouseListener);
});

export default viewportModule;
