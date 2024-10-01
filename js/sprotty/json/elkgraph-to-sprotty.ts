/**
 * # Copyright (c) 2024 ipyelk contributors.
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
  Dimension,
  Point,
  SEdge,
  SGraph,
  SLabel,
  SModelElement,
  SNode,
  SPort,
} from 'sprotty-protocol';

import {
  ElkEdge,
  ElkGraphElement,
  ElkLabel,
  ElkNode,
  ElkPort,
  ElkShape,
  isExtended,
  isPrimitive,
} from './elkgraph-json';
import { IElkSymbol, IElkSymbols, SElkConnectorSymbol } from './symbols';

/**
 * Checks the given type string and potentially returns the default type
 */
export function getType(type: string | undefined, defaultType: string = ''): string {
  if (type == null || type.length == 0) {
    return defaultType;
  }
  return type;
}

function getClasses(element: ElkGraphElement) {
  let classes = (element.properties?.cssClasses || '').trim();
  return classes ? classes.split(' ') : [];
}

export interface SSymbols extends SModelElement {}
export interface SSymbolGraph extends SGraph {
  symbols: SSymbols;
}

export interface ElkLabelschema extends SLabel {
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
    idPrefix: string,
  ): SSymbolGraph {
    let children = [];
    let edges = [];
    if (elkGraph.children) {
      children = elkGraph.children.map(this.transformElkNode, this);
    }
    if (elkGraph.edges) {
      edges = elkGraph.edges.map(this.transformElkEdge, this);
    }
    const sGraph: SSymbolGraph = {
      type: 'graph',
      id: elkGraph.id || 'root',
      children: [...children, ...edges],
      cssClasses: getClasses(elkGraph),
      symbols: this.transformSymbols(symbols, idPrefix),
    };
    return sGraph;
  }

  /**
   * Build up the Sprotty model objects for the SVG Symbols
   * @param symbols
   */
  private transformSymbols(symbols: IElkSymbols, idPrefix: string): SSymbols {
    let children = [];
    for (const key in symbols.library) {
      children.push(this.transformSymbol(key, symbols.library[key], idPrefix));
    }

    const sSymbols = {
      children: children,
    } as SSymbols;

    return sSymbols;
  }

  private transformSymbol(
    id: string,
    symbol: IElkSymbol,
    idPrefix: string,
  ): SModelElement {
    let element = symbol?.element;
    let children = [];
    if (element) {
      children = [this.transformSymbolElement(element)];
    }
    this.symbolsIds[id] = `${idPrefix}_${id}`;
    if (
      symbol.hasOwnProperty('symbol_offset') ||
      symbol.hasOwnProperty('path_offset')
    ) {
      this.connectors[id] = symbol as SElkConnectorSymbol;
    }

    return {
      type: 'symbol',
      id: id,
      children: children,
      position: this.pos(symbol),
      size: this.size(symbol),
      properties: symbol.properties,
    } as SModelElement;
  }

  private transformSymbolElement(elkNode: ElkNode): SNode {
    elkNode.properties.isSymbol = true;
    let sNode = {
      id: elkNode.id,
      position: this.pos(elkNode),
      size: this.size(elkNode),
      cssClasses: getClasses(elkNode),
      children: [],
      properties: elkNode.properties,
      type: getType(elkNode?.properties?.shape?.type, 'node'),
    } as SNode;
    const sNodes = elkNode.children.map(this.transformSymbolElement, this);
    sNode.children!.push(...sNodes);
    return sNode;
  }

  private transformElkNode(elkNode: ElkNode): SNode {
    this.checkAndRememberId(elkNode, this.nodeIds);

    const sNode = {
      type: getType(elkNode?.properties?.shape?.type, 'node'),
      id: elkNode.id,
      position: this.pos(elkNode),
      size: this.size(elkNode),
      children: [],
      cssClasses: getClasses(elkNode),
      properties: elkNode?.properties,
      layoutOptions: elkNode?.layoutOptions,
    } as SNode;
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

  private transformElkPort(elkPort: ElkPort): SPort {
    this.checkAndRememberId(elkPort, this.portIds);
    const sPort = {
      type: getType(elkPort.properties?.shape?.type, 'port'),
      id: elkPort.id,
      position: this.pos(elkPort),
      size: this.size(elkPort),
      children: [],
      cssClasses: getClasses(elkPort),
      properties: elkPort?.properties,
      layoutOptions: elkPort?.layoutOptions,
    } as SPort;
    // labels
    if (elkPort.labels) {
      const sLabels = elkPort.labels.map(this.transformElkLabel, this);
      sPort.children!.push(...sLabels);
    }
    return sPort;
  }

  private transformElkLabel(elkLabel: ElkLabel): ElkLabelschema {
    this.checkAndRememberId(elkLabel, this.labelIds);
    let sLabel = {
      type: getType(elkLabel.properties?.shape?.type, 'label'),
      id: elkLabel.id,
      text: elkLabel.text,
      position: this.pos(elkLabel),
      size: this.size(elkLabel),
      cssClasses: getClasses(elkLabel),
      labels: [],
      properties: elkLabel?.properties,
      layoutOptions: elkLabel?.layoutOptions,
    } as ElkLabelschema;
    if (elkLabel.labels) {
      const sLabels = elkLabel.labels.map(this.transformElkLabel, this);
      sLabel.labels!.push(...sLabels);
    }

    return sLabel;
  }

  private transformElkEdge(elkEdge: ElkEdge): SEdge {
    this.checkAndRememberId(elkEdge, this.edgeIds);

    const sEdge = {
      type: getType(elkEdge.properties?.shape?.type, 'edge'),
      id: elkEdge.id,
      sourceId: '',
      targetId: '',
      routingPoints: [],
      children: [],
      cssClasses: getClasses(elkEdge),
      properties: elkEdge?.properties,
      layoutOptions: elkEdge?.layoutOptions,
    } as SEdge;
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
        elkEdge.sections.forEach((section) => {
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
        const sJunction = {
          type: 'junction',
          id: elkEdge.id + '_j' + i,
          position: jp,
        } as SNode;
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
    return {
      width: elkShape.width || 0,
      height: elkShape.height || 0,
    } as Dimension;
  }

  private checkAndRememberId(e: ElkGraphElement, set: Set<string>) {
    if (e.id == null) {
      throw Error('An element is missing an id.');
    } else if (set.has(e.id)) {
      throw Error('Duplicate id: ' + e.id + '.');
    } else {
      set.add(e.id);
    }
  }
}
