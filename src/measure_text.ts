/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';

import { NAME, VERSION, ELK_CSS, ELK_DEBUG } from '.';

export class ELKTextSizerModel extends DOMWidgetModel {
  static model_name = 'ELKTextSizerModel';
  el: HTMLElement;
  label: HTMLElement;

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKTextSizerModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKTextSizerView.view_name,
      _view_module_version: VERSION
    };
    this.create_container();
    return defaults;
  }

  create_container() {
    ELK_DEBUG && console.warn('ELK Test Sizer Init');
    this.on('msg:custom', this.measure, this);

    this.el = document.body.appendChild(document.createElement('div'));
    this.el.classList.add('p-Widget', ELK_CSS.widget_class, ELK_CSS.sizer_class);
    this.el.innerHTML = `<svg><g><g><text class="${ELK_CSS.label}"></text></g></g></svg>`;

    this.label = <HTMLElement>this.el.getElementsByClassName('elklabel')[0];

    window.requestAnimationFrame(() => {
      // Modify element size after placed on DOM
      this.el.style.width = '0px';
      this.el.style.height = '0px';
    });
  }

  measure(content: IELKTextSizeRequest) {
    var value = content.text;
    this.label.innerHTML = escape(value);
    var size: DOMRect = this.label.getBoundingClientRect();

    const message: IELKTextSizeResponse = {
      event: 'measurement',
      text: value,
      width: size.width,
      height: size.height
    };
    ELK_DEBUG && console.warn('Sized Text', message);
    this.send((content = message), {}, []);
  }
}

export interface IELKTextSizeRequest {
  text: string;
}

export interface IELKTextSizeResponse extends IELKTextSizeRequest {
  event: 'measurement';
  width: number;
  height: number;
}

export class ELKTextSizerView extends DOMWidgetView {
  static view_name = 'ELKTextSizerView';

  model: ELKTextSizerModel;
  async render() {}
}

/**
 * Simple function to escape text for html before adding to dom
 */
function escape(text: string) {
  var tagsToReplace = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;'
  };
  return text.replace(/[&<>]/g, function(tag) {
    return tagsToReplace[tag] || tag;
  });
}
