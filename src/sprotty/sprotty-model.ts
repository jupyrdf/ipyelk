/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
// From https://github.com/OpenKieler/elkgraph-web
import {
  SNode,
  RectangularNode,
  RectangularPort,
  moveFeature,
  selectFeature,
  hoverFeedbackFeature,
  SEdge,
  editFeature,
  boundsFeature,
  alignFeature,
  layoutableChildFeature,
  edgeLayoutFeature,
  fadeFeature,
  SLabel,
} from 'sprotty';

import { ElkProperties } from './json/elkgraph-json';

export class ElkNode extends RectangularNode {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkPort extends RectangularPort {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkEdge extends SEdge {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === editFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkJunction extends SNode {
  hasFeature(feature: symbol): boolean {
    if (
      feature === moveFeature ||
      feature === selectFeature ||
      feature === hoverFeedbackFeature
    )
      return false;
    else return super.hasFeature(feature);
  }
}

export class ElkLabel extends SLabel {
  static readonly DEFAULT_FEATURES = [selectFeature, hoverFeedbackFeature, boundsFeature, alignFeature, layoutableChildFeature,
    edgeLayoutFeature, fadeFeature];
  properties: ElkProperties;
  labels: ElkLabel[];

  hasFeature(feature: symbol): boolean {
    if (feature === selectFeature || feature === hoverFeedbackFeature){
      if (this.properties?.selectable !== false){
        return true;
      }
    }
    else return super.hasFeature(feature);
  }
}

export class DefNode extends SNode {
  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}
