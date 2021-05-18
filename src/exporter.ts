/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { WidgetModel, WidgetView } from '@jupyter-widgets/base';

import { unpack_models as deserialize } from '@jupyter-widgets/base';

import { ELK_DEBUG, NAME, VERSION } from './tokens';

import { ELKViewerModel } from './display_widget';

import elkRawCSS from '!!raw-loader!../style/diagram.css';

import materialRawCss from '!!raw-loader!@jupyterlab/apputils/style/materialcolors.css';

import labRawCss from '!!raw-loader!@jupyterlab/theme-light-extension/style/variables.css';

const STANDALONE_CSS = `
  ${materialRawCss}
  ${labRawCss}
  ${elkRawCSS}
`
  .replace(/\/\*(.|\n)*?\*\//gm, ' ')
  .replace(/.jp-ElkView /g, '')
  .replace(/\n/g, ' ')
  .replace(/\s+/g, ' ')
  .replace(/\}/g, '}\n');

const XML_HEADER = '<?xml version="1.0" standalone="no"?>';

export class ELKExporterModel extends WidgetModel {
  static model_name = 'ELKExporterModel';
  private _update_timeout: number;

  static serializers = {
    ...WidgetModel.serializers,
    viewer: { deserialize },
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
      viewer: null,
      value: null,
      enabled: true,
      extra_css: '',
      padding: 20,
      diagram: null,
      strip_ids: true,
      add_xml_header: true
    };
    return defaults;
  }

  get enabled(): boolean {
    return this.get('enabled') || true;
  }

  get viewer(): ELKViewerModel {
    return this.get('viewer');
  }

  get diagram(): WidgetModel {
    return this.get('diagram');
  }

  get diagram_raw_css(): string[] {
    return this.diagram?.get('raw_css') || [];
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    this.on('change:viewer', this._on_viewer_changed, this);
    this.on('change:diagram', this._on_diagram_changed, this);
    this._on_viewer_changed();
    this._on_diagram_changed();
  }

  _on_viewer_changed() {
    ELK_DEBUG && console.warn('[export] viewer changed', arguments);
    if (this.viewer?.layoutUpdated == null) {
      return;
    }
    this.viewer.layoutUpdated.connect(this._schedule_update, this);
    if (!this.enabled) {
      return;
    }
    this._schedule_update();
  }

  is_an_elkmodel(model: WidgetModel) {
    return model instanceof ELKViewerModel;
  }

  _on_diagram_changed() {
    ELK_DEBUG && console.warn('[export] diagram changed', arguments);
    const { diagram } = this;
    if (diagram?.on != null) {
      diagram.on('change:raw_css', this._schedule_update, this);
      const children: WidgetModel[] = diagram.get('children') || [];
      const viewers = children.filter(this.is_an_elkmodel) as ELKViewerModel[];
      if (viewers.length && viewers[0].layoutUpdated) {
        viewers[0].layoutUpdated.connect(this._schedule_update, this);
      } else {
        ELK_DEBUG && console.warn('[export] no diagram ready', children);
      }
    }
  }

  async a_view(): Promise<WidgetView | null> {
    if (!this.enabled) {
      return;
    }
    let views = this.viewer.views;

    if (this.diagram?.views) {
      views = { ...views, ...this.diagram.views };
    }

    if (!Object.keys(views).length) {
      return;
    }

    for (const promise of Object.values(views)) {
      const view = (await promise) as WidgetView;
      if (view.el) {
        await view.displayed;
        return view;
      }
    }
  }

  _schedule_update() {
    if (!this.enabled) {
      return;
    }
    if (this._update_timeout != null) {
      window.clearInterval(this._update_timeout);
      this._update_timeout = null;
    }
    // does weird stuff with `this` apparently
    this._update_timeout = setTimeout(() => this._on_layout_updated(), 1000);
  }

  async _on_layout_updated() {
    if (!this.enabled) {
      return;
    }
    const view = await this.a_view();
    const svg: HTMLElement = view?.el?.querySelector('svg');
    if (svg == null) {
      this._schedule_update();
      return;
    }
    const { outerHTML } = svg;
    const padding = this.get('padding');
    const strip_ids = this.get('strip_ids');
    const add_xml_header = this.get('add_xml_header');
    const raw_diagram_css = this.diagram_raw_css;
    const rawStyle = `
        ${STANDALONE_CSS}
        ${raw_diagram_css.join('\n')}
        ${this.get('extra_css') || ''}
    `;
    const style = `
      <style type="text/css">
        <![CDATA[
          ${rawStyle}
        ]]>
      </style>`;
    const g: SVGGElement = svg.querySelector('g');
    const transform = g.attributes['transform'].value;
    let scaleFactor = 1.0;
    const scale = transform.match(/scale\((.*?)\)/);
    if (scale != null) {
      scaleFactor = parseFloat(scale[1]);
    }
    const { width, height } = g.getBoundingClientRect();

    let withCSS = outerHTML
      .replace(
        /<svg([^>]+)>/,
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width / scaleFactor +
          padding} ${height / scaleFactor + padding}" $1>
          ${style}
        `
      )
      .replace(/ transform=".*?"/, '');

    if (strip_ids) {
      withCSS = withCSS.replace(/\s*id="[^"]*"\s*/g, ' ');
    }

    if (add_xml_header) {
      withCSS = `${XML_HEADER}\n${withCSS}`;
    }

    this.set({ value: withCSS });

    this.save_changes(view.callbacks);
  }
}

export class ELKExporterView extends WidgetView {
  static view_name = 'ELKExporterView';
  model: ELKExporterModel;
}
