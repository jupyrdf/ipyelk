/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { WidgetModel, WidgetView } from '@jupyter-widgets/base';
import { unpack_models as deserialize } from '@jupyter-widgets/base';

import { ELKViewerModel, ELKViewerView } from './display_widget';
import { ELK_DEBUG, NAME, VERSION } from './tokens';

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
  private _update_timeout: number | null;

  static serializers = {
    ...WidgetModel.serializers,
    viewer: { deserialize },
    diagram: { deserialize },
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
      add_xml_header: true,
    };
    return defaults;
  }

  get enabled(): boolean {
    return this.get('enabled') !== false;
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
    if (this.viewer?.diagramUpdated == null) {
      return;
    }
    this.viewer.diagramUpdated.connect(this._schedule_update, this);
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
      if (viewers.length && viewers[0].diagramUpdated) {
        viewers[0].diagramUpdated.connect(this._schedule_update, this);
      } else {
        ELK_DEBUG && console.warn('[export] no diagram ready', children);
      }
    }
  }

  /**
   * Every viewer model this exporter draws from: the linked viewer, and any
   * viewer among a diagram's children.
   */
  viewer_models(): ELKViewerModel[] {
    const children: WidgetModel[] = this.diagram?.get('children') || [];
    const models = [this.viewer, ...children.filter(this.is_an_elkmodel)];
    return models.filter((model) => model != null) as ELKViewerModel[];
  }

  /**
   * The first displayed Sprotty viewer view, which can render the complete
   * diagram whatever its viewport currently shows.
   */
  async a_viewer_view(): Promise<ELKViewerView | null> {
    for (const model of this.viewer_models()) {
      for (const promise of Object.values(model.views || {})) {
        const view = (await promise) as WidgetView;
        if (view instanceof ELKViewerView && view.el) {
          await view.displayed;
          return view;
        }
      }
    }
    return null;
  }

  /**
   * The diagram's markup and its size in model coordinates.
   *
   * A viewer renders the whole diagram for the export, so scrolling or zooming
   * the diagram cannot crop what is exported. Without one -- a viewer that
   * never initialized Sprotty -- fall back to the rendered DOM, which holds
   * only what that viewport showed.
   */
  async capture_svg(): Promise<{
    markup: string;
    width: number;
    height: number;
  } | null> {
    const exported = (await this.a_viewer_view())?.exportSvg();
    if (exported != null) {
      const { markup, extent } = exported;
      return { markup, width: extent.width, height: extent.height };
    }

    const view = await this.a_view();
    const svg: SVGElement = view?.el?.querySelector('svg');
    const g: SVGGElement = svg?.querySelector('g');
    if (svg == null || g == null) {
      return null;
    }
    let scaleFactor = 1.0;
    const scale = g.attributes['transform']?.value?.match(/scale\((.*?)\)/);
    if (scale != null) {
      scaleFactor = parseFloat(scale[1]);
    }
    const { width, height } = g.getBoundingClientRect();
    return {
      markup: svg.outerHTML,
      width: width / scaleFactor,
      height: height / scaleFactor,
    };
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
      window.clearTimeout(this._update_timeout);
      this._update_timeout = null;
    }
    this._update_timeout = window.setTimeout(() => this._on_layout_updated(), 1000);
  }

  async _on_layout_updated() {
    if (!this.enabled) {
      return;
    }
    const view = await this.a_view();
    const captured = await this.capture_svg();
    if (captured == null) {
      this._schedule_update();
      return;
    }
    const { markup, width, height } = captured;
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
    let withCSS = markup
      .replace(
        /<svg([^>]+)>/,
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width + padding} ${
          height + padding
        }" $1>
          ${style}
        `,
      )
      // drop the viewport transform: the export is in model coordinates
      .replace(/ transform=".*?"/, '');

    if (strip_ids) {
      withCSS = withCSS.replace(/\s*id="[^"]*"\s*/g, ' ');
    }

    if (add_xml_header) {
      withCSS = `${XML_HEADER}\n${withCSS}`;
    }

    this.set({ value: withCSS });

    this.save_changes(view?.callbacks);
  }
}

export class ELKExporterView extends WidgetView {
  static view_name = 'ELKExporterView';
  model: ELKExporterModel;
}
