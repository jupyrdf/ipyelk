/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import PKG from '../package.json';

export const NAME = PKG.name;
export const VERSION = PKG.version;

export const ELK_DEBUG = window.location.hash.indexOf('ELK_DEBUG') > -1;

export interface IELKCenterMessage {
  action: 'center';
  model_id: string[] | string;
  animate?: boolean;
  retain_zoom?: boolean;
}

export interface IELKFitMessage {
  action: 'fit';
  model_id: string[] | string;
  animate?: boolean;
  max_zoom?: number;
  padding?: number;
}

export interface IRunMessage {
  action: 'run';
  /** the kernel's roundtrip generation, echoed back as `outlet.gen`; absent from older kernels */
  gen?: number;
}

// a `type`, not an `interface`: `WidgetModel.send` takes a `JSONValue`
export type TELKErrorMessage = {
  action: 'error';
  error: string;
  /** the generation of the `run` request that failed, if any */
  gen?: number;
};

export const ELK_CSS = {
  label: 'elklabel',
  widget_class: 'jp-ElkView',
  sizer_class: 'jp-ElkSizer',
};

export type TAnyELKMessage = IELKCenterMessage | IELKFitMessage;
