/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
// import Worker from '!!worker-loader!elkjs/lib/elk-worker.min.js';
import * as ELK from 'elkjs/lib/elk-api';

import { Signal } from '@lumino/signaling';

import { unpack_models as deserialize } from '@jupyter-widgets/base';
import { DOMWidgetModel } from '@jupyter-widgets/base';

import {
  applyProperties,
  layoutErrorMessage,
  prepareGraphForElk,
} from './layout_widget_util';
import { ELK_DEBUG, IRunMessage, NAME, VERSION } from './tokens';

import Worker from '!!worker-loader!elkjs/lib/elk-worker.js';

export { ELKTextSizerModel, ELKTextSizerView } from './measure_text';

const TheElk = new ELK.default({
  workerFactory: () => {
    ELK_DEBUG && console.warn('ELK Worker created');
    return new (Worker as any)();
  },
} as any);

export class ELKLayoutModel extends DOMWidgetModel {
  static model_name = 'ELKLayoutModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    inlet: { deserialize },
    outlet: { deserialize },
  };

  protected _elk: ELK.ELK;

  layoutUpdated = new Signal<ELKLayoutModel, void>(this);

  defaults() {
    let defaults = {
      ...super.defaults(),
      _view_module: NAME,
      _model_name: ELKLayoutModel.model_name,
      _model_module_version: VERSION,
      inlet: null,
      outlet: null,
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    // this.on('change:inlet', this.onInletChanged, this);
    // this.onInletChanged();
    this.on('msg:custom', this.handleMessage, this);
  }

  protected ensureElk() {
    if (this._elk == null) {
      this._elk = TheElk;
    }
  }

  handleMessage(content: IRunMessage) {
    // check message and decide if should call `measure`
    switch (content.action) {
      case 'run':
        this.layout();
        break;
    }
  }

  async layout() {
    // elkjs chokes on non-string element `properties`, and does not need
    // them -- prepareGraphForElk deep-copies the inlet value and strips them
    // off the copy (never the shared inlet value itself, which must survive
    // duplicate `run` messages / overlapping refreshes), and they are
    // reapplied onto the layout result afterwards.
    const rootNode: ELK.ElkNode = this.get('inlet')?.get('value');
    let outlet: DOMWidgetModel = this.get('outlet'); // target output
    if (rootNode == null || outlet == null) {
      return null;
    }
    const { graph, propmap } = prepareGraphForElk(rootNode);
    this.ensureElk();
    let result;
    try {
      result = await this._elk.layout(graph);
      // reapply properties
      applyProperties(result, propmap);
    } catch (error) {
      console.error(error);
      this.send(layoutErrorMessage(error));
      return null;
    }

    outlet.set('value', { ...result });
    outlet.save_changes();
    return result;
  }
}
