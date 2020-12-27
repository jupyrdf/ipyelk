/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
// From https://github.com/OpenKieler/elkgraph-web
import {
  SNode,
  RectangularNode,
  RectangularPort,
  moveFeature,
  selectFeature,
  hoverFeedbackFeature,
  SEdge,
  editFeature,
  SLabel,
  ViewRegistry,
  ModelRenderer,
  IVNodePostprocessor,
  RenderingTargetKind
} from 'sprotty';

import { JLModelSource } from './diagram-server';
import { SElkConnectorDef } from './json/defs';
import { ElkProperties } from './json/elkgraph-json';
import { VNode } from 'snabbdom/vnode';
import { WidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { html } from 'snabbdom-jsx';
import { Widget } from '@phosphor/widgets';

interface JLSprottyWidget {
  vnode: VNode;
  node: ElkNode;
  widget: WidgetModel;
}

function stopPropagation(ev){
  ev.preventDefault();
  ev.stopPropagation();
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

      let vnode = this.widgetContainer(this.widgets[key], args);
      if (vnode !== undefined) {
        vnodes.push(vnode);
      }
    }
    return vnodes;
  }

  widgetContainer(jlsw: Readonly<JLSprottyWidget>, args?: object): VNode | undefined {
    let bounds = jlsw.node.bounds;
    let style = {
      transform: `translate(${bounds.x}px, ${bounds.y}px)`,
      width: `${bounds.width}px`,
      height: `${bounds.height}px`,
      background: '#9dd8d857'
    };

    return html(
      'div',
      {
        style: style,
        hook: {
          insert: vnode => this.renderWidget(vnode, jlsw)
        },
        on: {
          click: [stopPropagation]
        }
      },
      []
    );
  }

  async renderWidget(vnode: VNode, jlsw: JLSprottyWidget, args?: object) {
    let widget = jlsw.widget;
    let view:DOMWidgetView = await this.source.widget_manager.create_view(widget, {});
    Widget.attach(view.pWidget, vnode.elm as HTMLElement)
  }

  async registerWidget(vnode: VNode | undefined, node: ElkNode) {
    let id = node.properties?.shape?.use;
    if (id) {
      let widget = await this.source.widget_manager.get_model(id);
      this.widgets[node.id] = { vnode: vnode, node: node, widget: widget };
    }
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

export class ElkNode extends RectangularNode {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkPort extends RectangularPort {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkEdge extends SEdge {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === editFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkJunction extends SNode {
  hasFeature(feature: symbol): boolean {
    if (
      feature === moveFeature ||
      feature === selectFeature ||
      feature === hoverFeedbackFeature
    )
      return false;
    else return super.hasFeature(feature);
  }
}

export class ElkLabel extends SLabel {
  properties: ElkProperties;
}

export class DefNode extends SNode {
  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefsNode extends SNode {
  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}
