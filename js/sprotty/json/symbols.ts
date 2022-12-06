/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { Point, SModelElementSchema } from 'sprotty';

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
  library: {
    [key: string]: IElkSymbol;
  };
}

export interface SElkConnectorSymbol extends IElkSymbol {
  path_offset: Point;
  symbol_offset: Point;
}
