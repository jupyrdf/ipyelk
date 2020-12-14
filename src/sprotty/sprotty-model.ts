/**
 * Copyright (c) 2020 Dane Freeman.
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
  SLabel,
  Point,
  ViewRegistry,
  ModelRenderer,
  // RenderingContext,
  IVNodePostprocessor,
  RenderingTargetKind
} from 'sprotty';

import { JLModelSource } from './diagram-server';
import { SElkConnectorDef } from './json/defs';

export class ElkModelRenderer extends ModelRenderer {
  source: JLModelSource;

  constructor(
    readonly viewRegistry: ViewRegistry,
    readonly targetKind: RenderingTargetKind,
    postprocessors: IVNodePostprocessor[],
    source: JLModelSource
  ) {
    super(viewRegistry, targetKind, postprocessors);
    this.source = source;
  }

  getConnector(id): SElkConnectorDef {
    let connector: SElkConnectorDef = this.source.elkToSprotty?.connectors[id];
    return connector;
  }

  hrefID(id: string): string | undefined {
    if (id) {
      return this.source.elkToSprotty.defsIds[id];
    }
  }
}

export class ElkNode extends RectangularNode {
  use?: string;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkPort extends RectangularPort {
  use?: string;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class ElkEdge extends SEdge {
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
  use?: string;
}

export class DefNode extends SNode {
  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefsNode extends SNode {
  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefPath extends SNode {
  segments: Point[];
  closed: boolean;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefCircle extends SNode {
  radius: number;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefEllipse extends SNode {
  rx: number;
  ry: number;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefRect extends SNode {
  width: number;
  height: number;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}

export class DefRawSVG extends SNode {
  value: string;

  hasFeature(feature: symbol): boolean {
    if (feature === moveFeature) return false;
    else return super.hasFeature(feature);
  }
}
