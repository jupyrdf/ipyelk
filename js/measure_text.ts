/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { random } from 'lodash';

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { unpack_models as deserialize } from '@jupyter-widgets/base';

import {
  RunQueue,
  answer,
  layoutErrorMessage,
  staleMessage,
} from './layout_widget_util';
import { ElkLabel, ElkNode } from './sprotty/json/elkgraph-json';
import { ELK_CSS, ELK_DEBUG, IRunMessage, NAME, VERSION } from './tokens';

// import { ElkNode } from './sprotty/sprotty-model';

/** how long `measure` waits for an animation frame before measuring anyway */
const MEASURE_FALLBACK_MS = 250;

type TSize = { width: number; height: number };

/** what the measured size of a label depends on, apart from the widget's CSS */
function sizeKey(label: ElkLabel): string {
  return JSON.stringify([label.properties?.cssClasses ?? '', label.text ?? '']);
}

/** the label font of the theme, which changes with the theme and its font size */
function themeFont(): string[] {
  if (typeof document === 'undefined') {
    return [];
  }
  const style = window.getComputedStyle(document.documentElement);
  return ['--jp-elk-label-font', '--jp-elk-label-font-size'].map((name) =>
    style.getPropertyValue(name),
  );
}

export class ELKTextSizerModel extends DOMWidgetModel {
  static model_name = 'ELKTextSizerModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    inlet: { deserialize },
    outlet: { deserialize },
  };

  /** one measurement in flight; re-sent requests are ignored, newer ones queued */
  protected runs = new RunQueue((gen) => this.runMeasure(gen));

  /** the sizes of the last run, by `sizeKey`, valid while the CSS is `sizesCss` */
  protected sizes = new Map<string, TSize>();
  protected sizesCss: string | null = null;

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
      outlet: null,
    };
    return defaults;
  }

  initialize(
    attributes: any,
    options: {
      model_id: string;
      comm?: any;
      widget_manager: any;
    },
  ) {
    super.initialize(attributes, options);
    ELK_DEBUG && console.warn('ELK Test Sizer Init');
    this.on('msg:custom', this.handleMessage, this);
    ELK_DEBUG && console.warn('ELK Text Done Init');
  }

  make_container(): HTMLElement {
    const el: HTMLElement = document.createElement('div');
    const styledClass = this.get('_dom_classes').filter(
      (dc: string) => dc.indexOf('styled-widget-') === 0,
    )[0];
    el.classList.add(
      'lm-Widget',
      ELK_CSS.widget_class,
      ELK_CSS.sizer_class,
      styledClass,
    );
    const sprotty = document.createElement('div');
    sprotty.classList.add('sprotty');
    const style = document.createElement('style');
    style.textContent = this.get('namespaced_css');
    const svg = createSVGElement('svg');
    svg.classList.add('sprotty-graph');
    svg.appendChild(createSVGElement('g'));
    sprotty.append(style, svg);
    el.appendChild(sprotty);
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
        this.runs.request(content.gen);
        break;
    }
  }

  /**
   * `measure`, reporting synchronous failures so the kernel stops retrying
   * instead of waiting for the roundtrip deadline.
   */
  protected runMeasure(gen: number): Promise<void> | null {
    try {
      return this.measure(gen);
    } catch (error) {
      console.error('ELK text sizer failed:', error);
      this.send(layoutErrorMessage(error, gen));
      return null;
    }
  }

  /**
   * Method to take a list of texts and build SVG Text Elements to attach to the DOM.
   *
   * Measures on the next animation frame, or after `MEASURE_FALLBACK_MS` in a
   * background tab, which never paints: an unresolved measurement would hold
   * the `RunQueue` slot and the kernel would wait out its deadline.
   * @param gen the request's generation, written back with the sizes
   * @returns a promise resolving once the sizes are written to the outlet
   */
  measure(gen: number = 0): Promise<void> | null {
    const rootNode: ElkNode = this.get('inlet')?.get('value');
    let outlet: DOMWidgetModel = this.get('outlet'); // target output
    const stale = staleMessage(this.get('inlet'), rootNode, outlet);
    if (stale != null) {
      this.send(stale); // unservable: let the kernel re-sync the state
      return null;
    }
    ELK_DEBUG && console.log('Root Node:', rootNode);
    let texts: ElkLabel[] = this.reuse_sizes(get_labels(rootNode));
    if (!texts.length) {
      answer(outlet, { ...rootNode, out: random() }, gen);
      return null;
    }

    ELK_DEBUG && console.warn('ELK Text Sizer Measure', texts);
    const el: HTMLElement = this.make_container();
    const view: SVGElement = el.getElementsByTagName('g')[0];

    const new_g: SVGElement = createSVGElement('g');
    texts.forEach((text) => {
      new_g.appendChild(this.make_label(text));
    });
    view.appendChild(new_g);

    ELK_DEBUG && console.warn('ELK Text Sizer to add node', new_g);
    ELK_DEBUG && console.warn('ELK Text Sizer node', view);

    document.body.prepend(el);

    let elements: SVGElement[] = Array.from(new_g.getElementsByTagName('text'));

    ELK_DEBUG && console.warn('Sized Text');

    // Callback to take measurements and remove element from DOM
    return new Promise<void>((resolve) => {
      let done = false;
      let frame = 0;
      let timer = 0;
      const finish = () => {
        if (done) {
          return;
        }
        done = true;
        window.cancelAnimationFrame(frame);
        window.clearTimeout(timer);
        // a throw in this deferred callback is otherwise an unhandled error
        // nobody correlates with the pipe: report it like the sync path
        try {
          this.read_sizes(texts, elements);
          let output = { ...rootNode };
          output['out'] = random();
          answer(outlet, output, gen);
        } catch (error) {
          console.error('ELK text sizer failed:', error);
          this.send(layoutErrorMessage(error, gen));
        } finally {
          if (!ELK_DEBUG && el.parentNode) {
            document.body.removeChild(el);
          }
          resolve();
        }
      };
      frame = window.requestAnimationFrame(finish);
      timer = window.setTimeout(finish, MEASURE_FALLBACK_MS);
    });
  }

  /**
   * Give each label the size measured in the last run for the same text and CSS
   * classes, if the CSS of the widget and the font of the theme did not change.
   * The kernel sends back the old size of a label whose text changed, so the
   * size on a label cannot tell if it is still valid.
   * @param labels the labels to size
   * @returns the labels left to measure
   */
  reuse_sizes(labels: ElkLabel[]): ElkLabel[] {
    const css = JSON.stringify([
      this.get('namespaced_css'),
      this.get('_dom_classes'),
      themeFont(),
    ]);
    const last = css === this.sizesCss ? this.sizes : new Map<string, TSize>();
    this.sizesCss = css;
    // keep only the sizes of this run, so that the map does not grow
    this.sizes = new Map();
    const unmeasured: ElkLabel[] = [];
    for (const label of labels) {
      const key = sizeKey(label);
      const size = last.get(key);
      if (size) {
        label.width = size.width;
        label.height = size.height;
        this.sizes.set(key, size);
      } else {
        unmeasured.push(label);
      }
    }
    return unmeasured;
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
      if (size.width || size.height) {
        // a label that did not render measures 0: measure it again next time
        this.sizes.set(sizeKey(label), { width: size.width, height: size.height });
      }

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
      // a label whose shape has a width and a height is not measured
      if (!label?.properties?.shape?.width || !label?.properties?.shape?.height) {
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
