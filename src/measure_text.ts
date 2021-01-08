/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { NAME, VERSION, ELK_CSS, ELK_DEBUG } from '.';

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
    (<any>window).sizer = this;
    ELK_DEBUG && console.warn('ELK Text Done Init');
  }

  make_container(): HTMLElement {
    const el: HTMLElement = document.createElement('div');
    const styledClass = this.get('_dom_classes').filter(
      (dc: string) => dc.indexOf('styled-widget-') === 0
    )[0];
    el.classList.add(
      'p-Widget',
      ELK_CSS.widget_class,
      ELK_CSS.sizer_class,
      styledClass
    );
    const raw_css: string = this.get('namespaced_css'); //TODO should this `raw_css` string be escaped?
    el.innerHTML = `<div class="sprotty"><style>${raw_css}</style><svg class="sprotty-graph"><g></g></svg></div>`;
    return el;
  }

  /**
   * SVG Text Element for given text string
   * @param text
   */
  make_label(text: IELKText): SVGElement {
    ELK_DEBUG && console.warn('ELK Text Label for text', text);
    let label: SVGElement = createSVGElement('text');
    let classes: string[] = [ELK_CSS.label];
    if (text.cssClasses.length > 0) {
      classes = classes.concat(text.cssClasses.split(' '));
    }

    label.classList.add(...classes);
    label.textContent = text.value;
    ELK_DEBUG && console.warn('ELK Text Label', label);
    return label;
  }

  /**
   * Method to take a list of texts and build SVG Text Elements to attach to the DOM
   * @param content TextSize Request
   */
  measure(content: IELKTextSizeRequest) {
    ELK_DEBUG && console.warn('ELK Text Sizer Measure', content);
    const el: HTMLElement = this.make_container();
    const view: SVGElement = el.getElementsByTagName('g')[0];

    const new_g: SVGElement = createSVGElement('g');
    content.texts.forEach(text => {
      new_g.appendChild(this.make_label(text));
    });
    view.appendChild(new_g);

    ELK_DEBUG && console.warn('ELK Text Sizer to add node', new_g);
    ELK_DEBUG && console.warn('ELK Text Sizer node', view);

    document.body.prepend(el);

    let elements: SVGElement[] = Array.from(new_g.getElementsByTagName('text'));

    ELK_DEBUG && console.warn('Sized Text');

    // Callback to take measurements and remove element from DOM
    window.requestAnimationFrame(() => {
      const response: IELKTextSizeResponse = {
        event: 'measurement',
        measurements: this.read_sizes(content.texts, elements)
      };
      if (!ELK_DEBUG) {
        document.body.removeChild(el);
      }
      this.send(response, {}, []);
    });
  }

  /**
   * Read the given SVG Text Elements sizes and generate TextSize Objects
   * @param texts Original list of text strings requested to size
   * @param elements List of SVG Text Elements to get their respective bounding boxes
   */
  read_sizes(texts: IELKText[], elements: SVGElement[]): IELKTextSize[] {
    let measurements: IELKTextSize[] = [];
    let i = 0;
    for (let label of elements) {
      ELK_DEBUG && console.warn(label.innerHTML);
      const text: IELKText = texts[i];
      const size: DOMRect = label.getBoundingClientRect();

      let measurement: IELKTextSize = {
        id: text.id,
        width: size.width,
        height: size.height
      };

      measurements.push(measurement);
      i++;
    }
    ELK_DEBUG && console.warn('Measurements', measurements);
    return measurements;
  }
}

export interface IELKText {
  id: string;
  value: string;
  cssClasses: string;
}

export interface IELKTextSizeRequest {
  texts: IELKText[];
}

export interface IELKTextSize {
  id: string;
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
 * SVG Required Namespaced Element
 */
function createSVGElement(tag: string): SVGElement {
  return document.createElementNS('http://www.w3.org/2000/svg', tag);
}
