/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { SModelElementSchema, Point } from 'sprotty';
import { ElkNode, ElkProperties } from './elkgraph-json';

export interface IElement extends SModelElementSchema {
  x: number;
  y: number;
}

export interface IElkSymbol extends SModelElementSchema {
  element: ElkNode;
  properties: ElkProperties;
}

export interface IElkSymbols {
  [key: string]: IElkSymbol;
}

export interface SElkConnectorSymbol extends IElkSymbol {
  offset: Point;
  correction: Point;
}
