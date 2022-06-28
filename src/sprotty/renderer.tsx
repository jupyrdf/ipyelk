/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import {
  ViewRegistry,
  ModelRenderer,
  IVNodePostprocessor,
  RenderingTargetKind,
  SChildElement,
  BoundsAware,
  getAbsoluteBounds,
  Point,
  getSubType,
  SModelFactory,
  SModelRoot,
  // SNodeSchema
  SModelElement,
  // SChildElement,
  Bounds,
  add
} from 'sprotty';

import { JLModelSource } from './diagram-server';
import { SElkConnectorSymbol } from './json/symbols';
import { SSymbolGraphSchema } from './json/elkgraph-to-sprotty';
import { ElkNode } from './sprotty-model';
import { VNode } from 'snabbdom/vnode';
import { WidgetModel, DOMWidgetView, DOMWidgetModel } from '@jupyter-widgets/base';
import { html } from 'snabbdom-jsx';
import { Widget } from '@lumino/widgets';
import { ELK_DEBUG } from '../tokens';

interface JLSprottyWidget {
  vnode: VNode;
  node: ElkNode;
  widget: WidgetModel;
  visible: boolean;
  html: string;
}

/**
 * Custom Renderer allowing the layering of jupyterlab widgets on top of the
 * sprotty elements.
 */
export class ElkModelRenderer extends ModelRenderer {
  source: JLModelSource;
  widgets: Map<string, JLSprottyWidget>;

  constructor(
    readonly viewRegistry: ViewRegistry,
    readonly targetKind: RenderingTargetKind,
    postprocessors: IVNodePostprocessor[],
    source: JLModelSource
  ) {
    super(viewRegistry, targetKind, postprocessors);
    this.source = source;
    this.widgets = new Map();
  }

  getSelected(): ElkNode[] {
    let elements = [];
    if (this.source.selectedNodes?.length) {
      for (let selected of this.source.selectedNodes) {
        let element = this.source.getById(selected.id); // as ElkNode
        elements.push(element);
        // if (element instanceof ElkNode){
        //   elements.push(element);
        // }
      }
    }
    return elements;
  }
  /**
   * Method to render potential overlay controls based on the selected diagram node
   */
  renderJLOverlayControl(args?: object): VNode[] {
    ELK_DEBUG && console.log('render control overlay');
    let vnodes: VNode[] = [];
    if (this.source.control_overlay) {
      let selected = this.getSelected();
      // filter selectedNodes...
      if (selected.length == 0) {
        // exit is nothing is selected or no control_overlay
        return vnodes;
      }
      let overlay_widget = this.source.control_overlay;

      // let activeNode = selected[0];
      let elkNode = new ElkNode();
      // let size = activeNode.size
      let bounds = mergeBounds(selected);
      let size = {
        width: 0, //activeNode.size.width,
        height: 0
      };
      elkNode.id = selected[0].id + '_entropy';
      elkNode.type = 'node:widget';
      elkNode.position = add(bounds, { x: bounds.width, y: 0 });
      elkNode.size = size;
      elkNode.properties = {
        shape: {
          use: overlay_widget.model_id
        }
      };

      let jlsw: JLSprottyWidget = {
        vnode: undefined,
        node: elkNode,
        widget: overlay_widget.model_id,
        visible: true,
        html: undefined
      };

      let vnode = this.widgetContainer(jlsw, args, false);
      if (vnode !== undefined) {
        // this.decorate(vnode, jlsw.node);
        vnodes.push(vnode);
      }
    }

    return vnodes;
  }

  /**
   * Method iterate over the JupyterLab widgets and render the VNodes
   */
  renderJLNodeWidgets(args?: object): VNode[] {
    let vnodes: VNode[] = [];
    for (let key in this.widgets) {
      let jlsw: JLSprottyWidget = this.widgets[key];
      let vnode = this.widgetContainer(jlsw, args);
      if (vnode !== undefined) {
        this.decorate(vnode, jlsw.node);
        vnodes.push(vnode);
      }
    }
    return vnodes;
  }

  /**
   * Sprotty Container for a JupyterLab widget
   */
  widgetContainer(
    jlsw: Readonly<JLSprottyWidget>,
    args?: object,
    setBounds: boolean = true
  ): VNode | undefined {
    if (!jlsw.visible) {
      return;
    }

    let position = getPosition(jlsw.node);
    let style = {
      transform: `translate(${position.x}px, ${position.y}px)`
      // background: '#9dd8d857'
    };

    // Specify Node Bounds
    if (setBounds) {
      let bounds = jlsw.node.bounds;
      if (!bounds) {
        bounds = getAbsoluteBounds(jlsw.node);
      }
      style['width'] = `${bounds.width}px`;
      style['height'] = `${bounds.height}px`;
    }

    let props = {};
    if (jlsw.html) {
      props = { innerHTML: jlsw.html };
    }

    return html(
      'div',
      {
        key: jlsw.node.id,
        class: {
          elkcontainer: true
        },
        style: style,
        props: props,
        hook: {
          insert: vnode => this.renderContent(vnode, jlsw)
        }
      },
      []
    );
  }

  /**
   * Attaching JupyterLab widget to sprotty container
   */
  async renderContent(vnode: VNode, jlsw: JLSprottyWidget, args?: object) {
    if (getSubType(jlsw.node) == 'widget') {
      let widget = jlsw.widget;
      let widget_model: DOMWidgetModel;
      if (typeof widget === 'string' || widget instanceof String) {
        widget_model = await this.source.widget_manager.get_model(widget as any);
      } else {
        widget_model = widget;
      }
      let view: DOMWidgetView = await this.source.widget_manager.create_view(
        widget_model,
        {}
      );
      Widget.attach(view.pWidget, vnode.elm as HTMLElement);
    }
  }

  /**
   * Registration function for a particular sprotty element id as being needing
   * to be added to the overlay
   */
  async registerJLWidgetNode(
    vnode: VNode | undefined,
    node: ElkNode,
    visible: boolean
  ) {
    this.widgets[node.id] = await this.wrapJLWidget(vnode, node, visible);
  }

  async wrapJLWidget(
    vnode: VNode | undefined,
    node: ElkNode,
    visible: boolean
  ): Promise<JLSprottyWidget> {
    let widget, html;
    let id = node.properties?.shape?.use;
    if (getSubType(node) == 'widget') {
      if (id) {
        widget = await this.source.widget_manager.get_model(id);
        html = undefined;
      }
    } else {
      widget = undefined;
      html = id;
    }

    return {
      vnode: vnode,
      node: node,
      widget: widget,
      visible: visible,
      html: html
    };
  }

  getConnector(id): SElkConnectorSymbol {
    let connector: SElkConnectorSymbol = this.source.elkToSprotty?.connectors[id];
    return connector;
  }

  hrefID(id: string): string | undefined {
    if (id) {
      return this.source.elkToSprotty.symbolsIds[id];
    }
  }
}

function getPosition(element: BoundsAware & SChildElement): Point {
  let x = 0;
  let y = 0;
  while (element !== undefined) {
    x = x + (element.bounds?.x || 0);
    y = y + (element.bounds?.y || 0);
    element = element?.parent as BoundsAware & SChildElement;
  }

  return {
    x: x,
    y: y
  };
}

export class SSymbolModelFactory extends SModelFactory {
  root: SModelRoot;

  protected initializeRoot(root: SModelRoot, schema: SSymbolGraphSchema): SModelRoot {
    root = super.initializeRoot(root, schema);

    if ((root as any)?.symbols) {
      (root as any).symbols.children = schema.symbols.children.map(childSchema =>
        this.createElement(childSchema, root)
      );
    }
    // TODO is there a better way to get a handle to the active `SModelRoot`?
    this.root = root;
    return root;
  }
}

type BBox = [number, number, number, number];

/*
 * Merge Bounds of SModelElements
 */
export function mergeBounds(elements: SModelElement[]): Bounds {
  let [minLeft, minBottom, maxRight, maxTop] = extents(elements[0]);

  elements.splice(1, elements.length).forEach(element => {
    let [left, bottom, right, top] = extents(element);
    if (left < minLeft) minLeft = left;
    if (bottom > minBottom) minBottom = bottom;
    if (right > maxRight) maxRight = right;
    if (top < maxTop) maxTop = top;
  });

  let bounds = {
    x: minLeft,
    y: maxTop,
    height: minBottom - maxTop,
    width: maxRight - minLeft
  };
  return bounds;
}

/*
 * Get SModelElement absolute bounds
 */
function extents(element: SModelElement): BBox {
  let bounds = getAbsoluteBounds(element);
  let left = bounds.x;
  let top = bounds.y;
  let right = bounds.x + bounds.width;
  let bottom = bounds.y + bounds.height;
  return [left, bottom, right, top];
}
