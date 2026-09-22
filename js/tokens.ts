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
  /**
   * The kernel's roundtrip generation for this pipe (`browser_roundtrip`);
   * the answer is written back as `outlet.gen` with the value. Absent from
   * older kernels.
   */
  gen?: number;
}

// a `type`, not an `interface`: `WidgetModel.send` takes a `JSONValue`
export type TELKErrorMessage = {
  action: 'error';
  error: string;
  /**
   * The generation of the `run` request that failed, so the kernel rejects
   * only the roundtrip still pending for it (a late error from an abandoned
   * generation is ignored). Absent when the failure is not tied to a request.
   */
  gen?: number;
};

export const ELK_CSS = {
  label: 'elklabel',
  widget_class: 'jp-ElkView',
  sizer_class: 'jp-ElkSizer',
};

export type TAnyELKMessage = IELKCenterMessage | IELKFitMessage;
