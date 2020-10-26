/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { WidgetModel, WidgetView } from '@jupyter-widgets/base';

import { unpack_models as deserialize } from '@jupyter-widgets/base';

import { NAME, VERSION } from '.';

import { ELKModel, ELKView } from './widget';

import elkRawCSS from '!!raw-loader!../style/diagram.css';

import materialRawCss from '!!raw-loader!@jupyterlab/apputils/style/materialcolors.css';

import labRawCss from '!!raw-loader!@jupyterlab/theme-light-extension/style/variables.css';

const STANDALONE_CSS = `
  ${materialRawCss}
  ${labRawCss}
  ${elkRawCSS.replace(/.jp-ElkView .sprotty /g, '')}
`;

const XML_HEADER = '<?xml version="1.0" standalone="no"?>';

export class ELKExporterModel extends WidgetModel {
  static model_name = 'ELKExporterModel';
  private _update_timeout: number;

  static serializers = {
    ...WidgetModel.serializers,
    diagram: { deserialize }
  };

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKExporterModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKExporterView.view_name,
      _view_module_version: VERSION,
      diagram: null,
      value: null,
      format: 'svg',
      enabled: true,
      extra_css: '',
      padding: 20
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    this.on('change:diagram', this._on_diagram_changed, this);
    this._on_diagram_changed();
  }

  _on_diagram_changed() {
    const { diagram } = this;
    if (diagram == null) {
      return;
    }
    this.diagram.layoutUpdated.connect(this._schedule_update, this);
    this._schedule_update();
  }

  async a_view() {
    const { views } = this.diagram;
    if (views == null) {
      return;
    }

    for (const promise of Object.values(views)) {
      const view = (await promise) as ELKView;
      if (view.el) {
        return view;
      }
    }
  }

  _schedule_update() {
    if (this._update_timeout != null) {
      window.clearInterval(this._update_timeout);
      this._update_timeout = null;
    }
    // does weird stuff with `this` apparently
    this._update_timeout = setTimeout(() => this._on_layout_updated(), 300);
  }

  async _on_layout_updated() {
    const view = await this.a_view();
    const svg: HTMLElement = view?.el?.querySelector('svg');
    if (svg == null) {
      return;
    }
    const { outerHTML } = svg;
    const padding = this.get('padding');
    const style = `<style>
      ${STANDALONE_CSS}
      ${this.get('extra_css') || ''}
    </style>`;
    const g: SVGGElement = svg.querySelector('g');
    const transform = g.attributes['transform'].value;
    let scaleFactor = 1.0;
    const scale = transform.match(/scale\((.*?)\)/);
    if (scale != null) {
      scaleFactor = parseFloat(scale[1]);
    }
    const { width, height } = g.getBoundingClientRect();

    const withCSS = outerHTML
      .replace(
        /<svg(.*)>/,
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width / scaleFactor +
          padding} ${height / scaleFactor + padding}" $1>`
      )
      .replace(/ transform=".*?"/, '')
      .replace('</svg>', `${style}</svg>`);
    this.set({ value: `${XML_HEADER}\n${withCSS}` });

    this.save_changes(view.callbacks);
  }

  get diagram(): ELKModel {
    return this.get('diagram');
  }
}

export class ELKExporterView extends WidgetView {
  static view_name = 'ELKExporterView';
  model: ELKExporterModel;
}
