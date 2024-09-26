/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';

import { Application, IPlugin } from '@lumino/application';
import { Widget } from '@lumino/widgets';

import { IJupyterWidgetRegistry } from '@jupyter-widgets/base';

import '../style/index.css';

import { ELK_DEBUG, NAME, VERSION } from './tokens';

const EXTENSION_ID = `${NAME}:plugin`;

const plugin: IPlugin<Application<Widget>, void> = {
  id: EXTENSION_ID,
  requires: [IJupyterWidgetRegistry],
  autoStart: true,
  activate: (app: Application<Widget>, registry: IJupyterWidgetRegistry) => {
    ELK_DEBUG && console.warn('elk activated');
    registry.registerWidget({
      name: NAME,
      version: VERSION,
      exports: async () => {
        const widgetExports = {
          ...(await import(/* webpackChunkName: "elklayout" */ './layout_widget')),
          ...(await import(/* webpackChunkName: "elkdisplay" */ './display_widget')),
          ...(await import(/* webpackChunkName: "elkexporter" */ './exporter')),
        };
        ELK_DEBUG && console.warn('widgets loaded');
        return widgetExports;
      },
    });
  },
};
export default plugin;
