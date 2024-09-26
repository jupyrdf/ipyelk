/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { Point, SModelElement } from 'sprotty-protocol';

import { ElkNode, ElkProperties } from './elkgraph-json';

export interface IElement extends SModelElement {
  x: number;
  y: number;
}

export interface IElkSymbol extends SModelElement {
  element: ElkNode;
  properties: ElkProperties;
}

export interface IElkSymbols {
  library: {
    [key: string]: IElkSymbol;
  };
}

export interface SElkConnectorSymbol extends IElkSymbol {
  path_offset: Point;
  symbol_offset: Point;
}
