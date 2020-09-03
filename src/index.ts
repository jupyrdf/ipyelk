/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
export const NAME = '@jupyrdf/jupyter-elk';
export const VERSION = '0.1.3a0';

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

export type TAnyELKMessage = IELKCenterMessage | IELKFitMessage;
