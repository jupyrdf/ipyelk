/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import { SModelElementSchema, Point } from 'sprotty';
// import { Circle, Path, Rect } from '../views/def_views';

export interface IElement extends SModelElementSchema {
  x: number;
  y: number;
}

export interface IElkDef extends SModelElementSchema {
  elements: IElement[];
}

export interface IElkDefs {
  [key: string]: IElkDef;
}

export interface SElkConnectorDef extends IElkDef {
  offset: Point;
  correction: Point;
}
