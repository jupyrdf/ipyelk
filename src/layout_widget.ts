/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { Signal } from '@lumino/signaling';

import { DOMWidgetModel } from '@jupyter-widgets/base';
import { unpack_models as deserialize } from '@jupyter-widgets/base';
// import Worker from '!!worker-loader!elkjs/lib/elk-worker.min.js';
import Worker from '!!worker-loader!elkjs/lib/elk-worker.js';
import * as ELK from 'elkjs/lib/elk-api';
import { NAME, VERSION, ELK_DEBUG } from './tokens';

import { ElkNode } from './sprotty/json/elkgraph-json';
export { ELKTextSizerModel, ELKTextSizerView } from './measure_text';

// export interface MarkElementWidget {
//   value
// }


const TheElk = new ELK.default({
  workerFactory: () => {
    ELK_DEBUG && console.warn('ELK Worker created');
    return new (Worker as any)();
  }
} as any);

function collectProperties(node: ElkNode) {
  let props: Map<string, any> = new Map();

  function strip(node) {
    props[node.id] = node.properties;
    delete node['properties'];
    // children
    if (node.children) {
      node.children.map(strip);
    }
    // ports
    if (node.ports) {
      node.ports.map(strip);
    }
    // labels
    if (node.labels) {
      node.labels.map(strip);
    }
    // edges
    if (node.edges) {
      node.edges.map(strip);
    }
  }
  strip(node);
  return props;
}

function applyProperties(node: ElkNode, props: Map<string, any>) {
  function apply(node) {
    node.properties = props[node.id];

    // children
    if (node.children) {
      node.children.map(apply);
    }
    // ports
    if (node.ports) {
      node.ports.map(apply);
    }
    // labels
    if (node.labels) {
      node.labels.map(apply);
    }
    // edges
    if (node.edges) {
      node.edges.map(apply);
    }
  }
  apply(node);
  return node;
}

export class ELKLayoutModel extends DOMWidgetModel {
  static model_name = 'ELKLayoutModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    source: { deserialize },
    value: { deserialize }
  };

  protected _elk: ELK.ELK;

  layoutUpdated = new Signal<ELKLayoutModel, void>(this);

  defaults() {
    let defaults = {
      ...super.defaults(),
      _view_module: NAME,
      _model_name: ELKLayoutModel.model_name,
      _model_module_version: VERSION,
      source: null,
      value: null
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    this.on('change:source', this.on_source_changed, this);
    this.on_source_changed();
  }

  protected ensureElk() {
    if (this._elk == null) {
      this._elk = TheElk;
    }
  }

  async on_source_changed() {
    // TODO disconnect old ones
    console.log('todo elk layout');
    let source = this.get('source');
    if (source){

      source.on("change:value", this.layout, this);
      this.layout()
    }
    console.log(source);

  }


  async layout() {
    // There looks like a bug with how elkjs failing to process edge properties
    // if they are anything more than simple strings. Elkjs doesnt need to operate
    // on the information passed in `properties` from ipyelk to sprotty so this
    // will strip them before calling elk and then reapply after
    // const {rootNode} = this;
    const rootNode: ELK.ElkNode = this.get("source")?.get("value")
    let value: DOMWidgetModel = this.get("value"); // target output
    if (rootNode == null || value == null){
      return null
    }
    let propmap = collectProperties(rootNode);
    // strip properties out
    this.ensureElk();
    let result = await this._elk.layout(rootNode);
    // reapply properties
    applyProperties(result, propmap);
    value.set("value", {...result});
    value.save_changes();
    return result;
  }
}
