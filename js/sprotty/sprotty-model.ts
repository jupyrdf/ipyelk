/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
// From https://github.com/OpenKieler/elkgraph-web
import {
  RectangularNode,
  RectangularPort,
  SEdgeImpl,
  SLabelImpl,
  SNodeImpl,
  alignFeature,
  boundsFeature,
  edgeLayoutFeature,
  editFeature,
  fadeFeature,
  hoverFeedbackFeature,
  layoutableChildFeature,
  moveFeature,
  selectFeature,
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

export class ElkEdge extends SEdgeImpl {
  properties: ElkProperties;

  hasFeature(feature: symbol): boolean {
    if (feature === editFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkJunction extends SNodeImpl {
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

export class ElkLabel extends SLabelImpl {
  static readonly DEFAULT_FEATURES = [
    selectFeature,
    hoverFeedbackFeature,
    boundsFeature,
    alignFeature,
    layoutableChildFeature,
    edgeLayoutFeature,
    fadeFeature,
  ];
  properties: ElkProperties;
  labels: ElkLabel[];
  selected: boolean = false;
  hoverFeedback: boolean = false;

  hasFeature(feature: symbol): boolean {
    if (feature === selectFeature || feature === hoverFeedbackFeature) {
      if (this.properties?.selectable === true) {
        return true;
      }
    } else return super.hasFeature(feature);
  }
}

export class SymbolNode extends SNodeImpl {
  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}
