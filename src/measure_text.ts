/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';

import { NAME, VERSION } from '.';

const WIDGET_CLASS = 'jp-ElkView';
const DEFAULT_VALUE = '';

export class ELKTextSizerModel extends DOMWidgetModel {
  static model_name = 'ELKTextSizerModel';

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKTextSizerModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKTextSizerView.view_name,
      _view_module_version: VERSION,
      text: DEFAULT_VALUE,
      width: 0,
      height: 0
    };
    return defaults;
  }
}

export interface IELKTextSizeMessage {
  text: string;
}

export class ELKTextSizerView extends DOMWidgetView {
  static view_name = 'ELKTextSizerView';

  model: ELKTextSizerModel;
  svg: HTMLElement;
  label: HTMLElement;

  initialize(parameters: any) {
    super.initialize(parameters);
    // this.model.on('change:text', this.measure, this);
    console.log('init');
    this.model.on('msg:custom', this.measure, this);

    this.el = document.body.appendChild(document.createElement('div'));
    this.el.classList.add('p-Widget');
    this.el.classList.add(WIDGET_CLASS);

    this.el.innerHTML = '<svg><g><g><text class="elklabel"></text></g></g></svg>';
    this.el.style.width = '0px';
    this.el.style.height = '0px';
    console.log('height 0?>');

    this.label = <HTMLElement>this.el.getElementsByClassName('elklabel')[0];
  }

  async render() {}

  measure(content: IELKTextSizeMessage) {
    console.log('measure');
    console.log(content);
    var value = content.text;
    this.label.innerHTML = value;
    var size: DOMRect = this.label.getBoundingClientRect();
    // this.model.set('width', size.width);
    // this.model.set('height', size.height);
    // this.touch();

    var message = {
      event: 'measurement',
      text: value,
      width: size.width,
      height: size.height
    };
    console.log(message);
    this.send(message);
  }
}
