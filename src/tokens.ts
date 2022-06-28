/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
export const NAME = '@jupyrdf/jupyter-elk';
export const VERSION = '2.0.0-alpha1';

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
}

export const ELK_CSS = {
  label: 'elklabel',
  widget_class: 'jp-ElkView',
  sizer_class: 'jp-ElkSizer'
};

export type TAnyELKMessage = IELKCenterMessage | IELKFitMessage;
