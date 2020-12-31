/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import {
  ViewRegistry,
  ModelRenderer,
  IVNodePostprocessor,
  RenderingTargetKind,
  SChildElement,
  BoundsAware,
  Point,
  getSubType
} from 'sprotty';

import { JLModelSource } from './diagram-server';
import { SElkConnectorDef } from './json/defs';
import { ElkNode } from './sprotty-model';
import { VNode } from 'snabbdom/vnode';
import { WidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { html } from 'snabbdom-jsx';
import { Widget } from '@phosphor/widgets';

interface JLSprottyWidget {
  vnode: VNode;
  node: ElkNode;
  widget: WidgetModel;
  visible: boolean;
  html: string;
}

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

  renderWidgets(args?: object): VNode[] {
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

  widgetContainer(jlsw: Readonly<JLSprottyWidget>, args?: object): VNode | undefined {
    if (!jlsw.visible) {
      return;
    }
    let bounds = jlsw.node.bounds;
    let position = getPosition(jlsw.node);
    let style = {
      transform: `translate(${position.x}px, ${position.y}px)`,
      width: `${bounds.width}px`,
      height: `${bounds.height}px`,
      background: '#9dd8d857'
    };
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

  async renderContent(vnode: VNode, jlsw: JLSprottyWidget, args?: object) {
    if (getSubType(jlsw.node) == 'widget') {
      let widget = jlsw.widget;
      let view: DOMWidgetView = await this.source.widget_manager.create_view(
        widget,
        {}
      );
      Widget.attach(view.pWidget, vnode.elm as HTMLElement);
    }
  }

  async overlayContent(vnode: VNode | undefined, node: ElkNode, visible: boolean) {
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
    this.widgets[node.id] = {
      vnode: vnode,
      node: node,
      widget: widget,
      visible: visible,
      html: html
    };
  }

  getConnector(id): SElkConnectorDef {
    let connector: SElkConnectorDef = this.source.elkToSprotty?.connectors[id];
    return connector;
  }

  hrefID(id: string): string | undefined {
    if (id) {
      return this.source.elkToSprotty.defsIds[id];
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
