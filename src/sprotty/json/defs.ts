import { SModelElementSchema, Point } from 'sprotty';
// import { Circle, Path, Rect } from '../views/def_views';

type Constructor<T> = new (...args: any[]) => T;

export const json2Instance = <T>(
  source: object,
  destinationConstructor: Constructor<T>
): T => Object.assign(new destinationConstructor(), source);

export interface IElement extends SModelElementSchema {
  x: number;
  y: number;
}

export interface IElkDef extends SModelElementSchema {
  elements: IElement[];
}

export interface IConnectorDef extends IElkDef {
  offset: [number, number];
}

export interface IElkDefs {
  [key: string]: IElkDef;
}

export interface SElkConnectorDef extends IElkDef {
  offset: Point;
  correction: Point;
}
