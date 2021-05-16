/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { unpack_models as deserialize } from '@jupyter-widgets/base';
import { NAME, VERSION, ELK_CSS, ELK_DEBUG, IRunMessage } from './tokens';
import { ElkNode, ElkLabel } from './sprotty/json/elkgraph-json';
// import { ElkNode } from './sprotty/sprotty-model';

export class ELKTextSizerModel extends DOMWidgetModel {
  static model_name = 'ELKTextSizerModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    inlet: { deserialize },
    outlet: { deserialize }
  };

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKTextSizerModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKTextSizerView.view_name,
      _view_module_version: VERSION,
      id: String(Math.random()),
      inlet: null,
      outlet: null
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
    this.on('msg:custom', this.handleMessage, this);
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
  make_label(label: ElkLabel): SVGElement {
    ELK_DEBUG && console.warn('ELK Text Label for text', label);
    let element: SVGElement = createSVGElement('text');
    let classes: string[] = [ELK_CSS.label];
    if (label.properties?.cssClasses.length > 0) {
      classes = classes.concat(label.properties?.cssClasses.split(' '));
    }

    element.classList.add(...classes);
    element.textContent = label.text;
    ELK_DEBUG && console.warn('ELK Text Label', element);
    return element;
  }

  handleMessage(content: IRunMessage) {
    // check message and decide if should call `measure`
    switch (content.action) {
      case 'run':
        this.measure();
        break;
    }
  }

  /**
   * Method to take a list of texts and build SVG Text Elements to attach to the DOM
   * @param content message measure request
   */
  measure() {
    const rootNode: ElkNode = this.get('inlet')?.get('value');
    let outlet: DOMWidgetModel = this.get('outlet'); // target output
    if (rootNode == null || outlet == null) {
      return null;
    }
    ELK_DEBUG && console.log('Root Node:', rootNode);
    let texts: ElkLabel[] = get_labels(rootNode);

    ELK_DEBUG && console.warn('ELK Text Sizer Measure', texts);
    const el: HTMLElement = this.make_container();
    const view: SVGElement = el.getElementsByTagName('g')[0];

    const new_g: SVGElement = createSVGElement('g');
    texts.forEach(text => {
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
      this.read_sizes(texts, elements);
      outlet.set('value', { ...rootNode });
      outlet.save_changes();
      if (!ELK_DEBUG) {
        document.body.removeChild(el);
      }
    });
  }

  /**
   * Read the given SVG Text Elements sizes and generate TextSize Objects
   * @param texts Original list of text strings requested to size
   * @param elements List of SVG Text Elements to get their respective bounding boxes
   */
  read_sizes(labels: ElkLabel[], elements: SVGElement[]) {
    let i = 0;
    for (let element of elements) {
      ELK_DEBUG && console.warn(element.innerHTML);
      const label: ElkLabel = labels[i];
      const size: DOMRect = element.getBoundingClientRect();

      label.width = size.width;
      label.height = size.height;

      i++;
    }
  }
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

function get_labels(el: any): ElkLabel[] {
  let labels: ElkLabel[] = [];
  if (el?.labels) {
    for (let label of el.labels as ElkLabel[]) {
      // size only those labels without a width or a height set
      if (!label?.width || !label?.height) {
        labels.push(label);
      }
    }
  }
  for (let child of el?.ports || []) {
    labels.push(...get_labels(child));
  }
  for (let child of el?.children || []) {
    labels.push(...get_labels(child));
  }
  for (let edge of el?.edges || []) {
    labels.push(...get_labels(edge));
  }
  for (let label of el?.labels || []) {
    labels.push(...get_labels(label));
  }

  return labels;
}
