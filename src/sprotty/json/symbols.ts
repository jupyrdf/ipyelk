/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { SModelElementSchema, Point } from 'sprotty';

export interface IElement extends SModelElementSchema {
  x: number;
  y: number;
}

export interface IElkSymbol extends SModelElementSchema {
  elements: IElement[];
}

export interface IElkSymbols {
  [key: string]: IElkSymbol;
}

export interface SElkConnectorSymbol extends IElkSymbol {
  offset: Point;
  correction: Point;
}
