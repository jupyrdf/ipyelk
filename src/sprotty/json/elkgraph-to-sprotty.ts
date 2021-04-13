/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
/*******************************************************************************
 * Copyright (c) 2017 Kiel University and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *******************************************************************************/
import {
  SNodeSchema,
  SEdgeSchema,
  SPortSchema,
  SLabelSchema,
  SGraphSchema,
  Point,
  Dimension,
  SModelElementSchema
  // PopupModelViewer
} from 'sprotty';
import {
  ElkShape,
  ElkNode,
  ElkPort,
  ElkLabel,
  ElkEdge,
  ElkGraphElement,
  isPrimitive,
  isExtended
} from './elkgraph-json';

import { IElkSymbols, SElkConnectorSymbol } from './symbols';

/**
 * Checks the given type string and potentially returns the default type
 */
export function getType(type: string | undefined, defaultType: string = ''): string {
  if (type == undefined || type.length == 0) {
    return defaultType;
  }
  return type;
}

function getClasses(element: ElkGraphElement) {
  let classes = (element.properties?.cssClasses || '').trim();
  return classes ? classes.split(' ') : [];
}

export interface SSymbolsSchema extends SModelElementSchema {}
export interface SSymbolGraphSchema extends SGraphSchema {
  symbols: SSymbolsSchema;
}

export interface ElkLabelschema extends SLabelSchema {
  labels: ElkLabelschema[];
}

export class ElkGraphJsonToSprotty {
  private nodeIds: Set<string> = new Set();
  private edgeIds: Set<string> = new Set();
  private portIds: Set<string> = new Set();
  private labelIds: Set<string> = new Set();
  private sectionIds: Set<string> = new Set();
  symbolsIds: Map<string, string> = new Map();
  connectors: Map<string, SElkConnectorSymbol> = new Map();

  public transform(
    elkGraph: ElkNode,
    symbols: IElkSymbols,
    idPrefix: string
  ): SSymbolGraphSchema {
    const sGraph = <SSymbolGraphSchema>{
      type: 'graph',
      id: elkGraph.id || 'root',
      children: [],
      cssClasses: getClasses(elkGraph),
      symbols: this.transformSymbols(symbols, idPrefix)
    };

    if (elkGraph.children) {
      const children = elkGraph.children.map(this.transformElkNode, this);
      sGraph.children.push(...children);
    }
    if (elkGraph.edges) {
      const sEdges = elkGraph.edges.map(this.transformElkEdge, this);
      sGraph.children!.push(...sEdges);
    }

    return sGraph;
  }

  /**
   * Build up the Sprotty model objects for the SVG Symbols
   * @param symbols
   */
  private transformSymbols(symbols: IElkSymbols, idPrefix: string): SSymbolsSchema {
    let children = [];
    for (const key in symbols) {
      children.push(this.transformSymbol(key, symbols[key], idPrefix));
    }

    const sSymbols = <SSymbolsSchema>{
      children: children
    };

    return sSymbols;
  }

  private transformSymbol(
    id: string,
    symbol: ElkNode,
    idPrefix: string
  ): SModelElementSchema {
    let children = symbol?.children?.map(this.transformSymbolElement, this) || [];
    this.symbolsIds[id] = `${idPrefix}_${id}`;
    if (symbol?.properties?.type == 'connectorsymbol') {
      this.connectors[id] = <SElkConnectorSymbol>symbol;
    }

    return <SModelElementSchema>{
      type: 'symbol',
      id: id,
      children: children,
      position: this.pos(symbol),
      size: this.size(symbol),
      properties: symbol.properties
    };
  }

  private transformSymbolElement(elkNode: ElkNode): SNodeSchema {
    elkNode.properties.isSymbol = true;
    let element = <SNodeSchema>{
      id: elkNode.id,
      position: this.pos(elkNode),
      size: this.size(elkNode),
      children: [],
      properties: elkNode.properties,
      type: elkNode.properties?.type
    };
    return element;
  }

  private transformElkNode(elkNode: ElkNode): SNodeSchema {
    this.checkAndRememberId(elkNode, this.nodeIds);

    const sNode = <SNodeSchema>{
      type: getType(elkNode?.properties?.type, 'node'),
      id: elkNode.id,
      position: this.pos(elkNode),
      size: this.size(elkNode),
      children: [],
      cssClasses: getClasses(elkNode),
      properties: elkNode?.properties,
      layoutOptions: elkNode?.layoutOptions
    };
    // children
    if (elkNode.children) {
      const sNodes = elkNode.children.map(this.transformElkNode, this);
      sNode.children!.push(...sNodes);
    }
    // ports
    if (elkNode.ports) {
      const sPorts = elkNode.ports.map(this.transformElkPort, this);
      sNode.children!.push(...sPorts);
    }
    // labels
    if (elkNode.labels) {
      const sLabels = elkNode.labels.map(this.transformElkLabel, this);
      sNode.children!.push(...sLabels);
    }
    // edges
    if (elkNode.edges) {
      const sEdges = elkNode.edges.map(this.transformElkEdge, this);
      sNode.children!.push(...sEdges);
    }
    return sNode;
  }

  private transformElkPort(elkPort: ElkPort): SPortSchema {
    this.checkAndRememberId(elkPort, this.portIds);
    const sPort = <SPortSchema>{
      type: getType(elkPort.properties?.type, 'port'),
      id: elkPort.id,
      position: this.pos(elkPort),
      size: this.size(elkPort),
      children: [],
      cssClasses: getClasses(elkPort),
      properties: elkPort?.properties,
      layoutOptions: elkPort?.layoutOptions
    };
    // labels
    if (elkPort.labels) {
      const sLabels = elkPort.labels.map(this.transformElkLabel, this);
      sPort.children!.push(...sLabels);
    }
    return sPort;
  }

  private transformElkLabel(elkLabel: ElkLabel): ElkLabelschema {
    this.checkAndRememberId(elkLabel, this.labelIds);
    let sLabel = <ElkLabelschema>{
      type: getType(elkLabel.properties?.type, 'label'),
      id: elkLabel.id,
      text: elkLabel.text,
      position: this.pos(elkLabel),
      size: this.size(elkLabel),
      cssClasses: getClasses(elkLabel),
      labels: [],
      properties: elkLabel?.properties,
      layoutOptions: elkLabel?.layoutOptions
    };
    if (elkLabel.labels) {
      const sLabels = elkLabel.labels.map(this.transformElkLabel, this);
      sLabel.labels!.push(...sLabels);
    }

    return sLabel;
  }

  private transformElkEdge(elkEdge: ElkEdge): SEdgeSchema {
    this.checkAndRememberId(elkEdge, this.edgeIds);

    const sEdge = <SEdgeSchema>{
      type: getType(elkEdge.properties?.type, 'edge'),
      id: elkEdge.id,
      sourceId: '',
      targetId: '',
      routingPoints: [],
      children: [],
      cssClasses: getClasses(elkEdge),
      properties: elkEdge?.properties,
      layoutOptions: elkEdge?.layoutOptions
    };
    if (isPrimitive(elkEdge)) {
      sEdge.sourceId = elkEdge.source;
      sEdge.targetId = elkEdge.target;
      if (elkEdge.sourcePoint) sEdge.routingPoints!.push(elkEdge.sourcePoint);
      if (elkEdge.bendPoints) sEdge.routingPoints!.push(...elkEdge.bendPoints);
      if (elkEdge.targetPoint) sEdge.routingPoints!.push(elkEdge.targetPoint);
    } else if (isExtended(elkEdge)) {
      sEdge.sourceId = elkEdge.sources[0];
      sEdge.targetId = elkEdge.targets[0];
      if (elkEdge.sections) {
        elkEdge.sections.forEach(section => {
          this.checkAndRememberId(section, this.sectionIds);
          sEdge.routingPoints!.push(section.startPoint);
          if (section.bendPoints) {
            sEdge.routingPoints!.push(...section.bendPoints);
          }
          sEdge.routingPoints!.push(section.endPoint);
        });
      }
    }
    if (elkEdge.junctionPoints) {
      elkEdge.junctionPoints.forEach((jp, i) => {
        const sJunction = <SNodeSchema>{
          type: 'junction',
          id: elkEdge.id + '_j' + i,
          position: jp
        };
        sEdge.children!.push(sJunction);
      });
    }

    // labels
    if (elkEdge.labels) {
      const sLabels = elkEdge.labels.map(this.transformElkLabel, this);
      sEdge.children!.push(...sLabels);
    }
    return sEdge;
  }

  private pos(elkShape: ElkShape): Point {
    return { x: elkShape.x || 0, y: elkShape.y || 0 };
  }

  private size(elkShape: ElkShape): Dimension {
    return <Dimension>{
      width: elkShape.width || 0,
      height: elkShape.height || 0
    };
  }

  private checkAndRememberId(e: ElkGraphElement, set: Set<string>) {
    if (e.id == undefined) {
      throw Error('An element is missing an id.');
    } else if (set.has(e.id)) {
      throw Error('Duplicate id: ' + e.id + '.');
    } else {
      set.add(e.id);
    }
  }
}
