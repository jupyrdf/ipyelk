/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { NAME, VERSION, ELK_CSS, ELK_DEBUG } from '.';
import _ from 'underscore';

export class ELKTextSizerModel extends DOMWidgetModel {
  static model_name = 'ELKTextSizerModel';
  el: HTMLElement;
  label: HTMLElement;
  id: string;

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKTextSizerModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKTextSizerView.view_name,
      _view_module_version: VERSION,
      id: String(Math.random())
    };
    return defaults;
  }

  initialize(
    attributes: any,
    options: {
      model_id: string;
      comm?: any;
      widget_manager: any;
    }
  ) {
    super.initialize(attributes, options);
    ELK_DEBUG && console.warn('ELK Test Sizer Init');
    this.on('msg:custom', this.measure, this);

    this.el = document.body.appendChild(document.createElement('div'));
    this.el.classList.add('p-Widget', ELK_CSS.widget_class, ELK_CSS.sizer_class);
    this.el.innerHTML = `<div class=""><svg><g id="${this.id}"></g></svg></div>`;

    window.requestAnimationFrame(() => {
      // Modify element size after placed on DOM
      this.el.style.width = '100px';
      this.el.style.height = '0px';
    });
    this.listenToOnce(this, 'destroy', this.cleanup);
    ELK_DEBUG && console.warn('ELK Text Done Init');
  }

  make_label(text: IELKText): SVGElement {
    ELK_DEBUG && console.warn('ELK Text Label for text', text);
    let label: SVGElement = createSVGElement('text');
    let classes: string = '';
    if (text.cssClasses.length > 0) {
      classes = [text.cssClasses, ELK_CSS.label].join(' ');
    } else {
      classes = ELK_CSS.label;
    }

    label.classList.add(classes);
    label.textContent = escape(text.value);
    ELK_DEBUG && console.warn('ELK Text Label', label);
    return label;
  }

  measure(content: IELKTextSizeRequest) {
    ELK_DEBUG && console.warn('ELK Text Sizer Measure', content);
    let view: HTMLElement = document.getElementById(this.id);

    let new_g: SVGElement = createSVGElement('g');
    content.texts.forEach(text => {
      new_g.appendChild(this.make_label(text));
    });

    // triggering DOM refresh
    let old_g: SVGElement = view.getElementsByTagName('g')[0];
    if (old_g) {
      view.removeChild(old_g);
    }
    new_g = view.appendChild(new_g);
    ELK_DEBUG && console.warn('ELK Text Sizer to add node', new_g);
    ELK_DEBUG && console.warn('ELK Text Sizer node', view);

    let elements: SVGElement[] = Array.from(new_g.getElementsByTagName('text'));

    ELK_DEBUG && console.warn('Sized Text');
    window.requestAnimationFrame(() => {
      let response: IELKTextSizeResponse = {
        event: 'measurement',
        measurements: this.read_sizes(content.texts, elements)
      };
      this.send(response, {}, []);
    });
  }

  read_sizes(texts: IELKText[], elements: SVGElement[]): IELKTextSize[] {
    let measurements: IELKTextSize[] = [];
    let i = 0;
    for (let label of elements) {
      console.log(label.innerHTML);
      let text: IELKText = texts[i];
      var size: DOMRect = label.getBoundingClientRect();

      let measurement: IELKTextSize = {
        text: text.value,
        width: size.width,
        height: size.height
      };

      measurements.push(measurement);
      i++;
    }
    ELK_DEBUG && console.warn('Measurements', measurements);
    return measurements;
  }

  cleanup() {
    console.log('destroy me');
  }
}

export interface IELKText {
  value: string;
  cssClasses: string;
}

export interface IELKTextSizeRequest {
  texts: IELKText[];
}

export interface IELKTextSize {
  text: string;
  width: number;
  height: number;
}
export interface IELKTextSizeResponse {
  event: 'measurement';
  measurements: IELKTextSize[];
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

/**
 * SVG Required Namespaced Element
 */
function createSVGElement(tag: string): SVGElement {
  return document.createElementNS('http://www.w3.org/2000/svg', tag);
}
