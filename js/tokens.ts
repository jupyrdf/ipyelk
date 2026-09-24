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

/** `SprottyViewer.set_viewport`: `null` origin/zoom keep the view's value, `null`
 * view_id addresses every connected view. */
export interface IELKViewportMessage {
  action: 'viewport';
  origin: [number, number] | null;
  zoom: number | null;
  animate: boolean;
  view_id: string | null;
}

export interface IRunMessage {
  action: 'run';
}

export const ELK_CSS = {
  label: 'elklabel',
  widget_class: 'jp-ElkView',
  sizer_class: 'jp-ElkSizer',
};

export type TAnyELKMessage = IELKCenterMessage | IELKFitMessage | IELKViewportMessage;
