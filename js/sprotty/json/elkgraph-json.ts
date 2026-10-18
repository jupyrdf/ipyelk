/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */

/*******************************************************************************
 * Copyright (c) 2019 TypeFox and others.
 *
 * This program and the accompanying materials are made
 * available under the terms of the Eclipse Public License 2.0
 * which is available at https://www.eclipse.org/legal/epl-2.0/
 *
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
/**
 * The `identifier` of a symbol in the diagram's `defs`.
 * @minLength 1
 */
export type SymbolId = string;

/**
 * The `d` attribute of an SVG `path`: a move first, then path commands, numbers,
 * commas and spaces.
 * @pattern ^\s*[Mm][\sMmZzLlHhVvCcSsQqTtAa0-9eE+\-.,]*$
 */
export type PathData = string;

/** SVG or HTML markup. The views insert it as it is, so it must be trusted. */
export type Markup = string;

/**
 * The URL of an image: absolute, relative to the notebook, or a `data:` URL.
 * @minLength 1
 */
export type ImageUrl = string;

/**
 * The size of a comment's notch in pixels: a finite number, 0 or more. 0 draws no
 * notch. ipyelk 2.x wrote it as a string, which the view still reads.
 * @minimum 0
 */
export type NotchSize = number;

/** The `model_id` of the Jupyter widget that a `node:widget` shape draws. */
export type ModelId = string;

/** The fields that every shape can have. */
export interface ShapeBase {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  /** Milliseconds before a widget shape applies the diagram zoom; others ignore it. */
  delay?: number;
}

export interface EdgeShape extends ShapeBase {
  type: 'edge';
  start?: SymbolId;
  end?: SymbolId;
}

export interface PortShape extends ShapeBase {
  type: 'port';
  use?: SymbolId;
}

export interface LabelShape extends ShapeBase {
  type: 'label';
  use?: SymbolId;
}

export interface IconShape extends ShapeBase {
  type: 'label:icon';
  use: SymbolId;
}

export interface RectShape extends ShapeBase {
  type: 'node';
}

export interface PathShape extends ShapeBase {
  type: 'node:path';
  use: PathData;
}

export interface SVGShape extends ShapeBase {
  type: 'node:svg';
  use: Markup;
}

export interface RoundShape extends ShapeBase {
  type: 'node:round';
}

export interface DiamondShape extends ShapeBase {
  type: 'node:diamond';
}

export interface CommentShape extends ShapeBase {
  type: 'node:comment';
  use?: NotchSize;
}

export interface UseShape extends ShapeBase {
  type: 'node:use';
  use: SymbolId;
}

export interface ImageShape extends ShapeBase {
  type: 'node:image';
  use: ImageUrl;
}

export interface ForeignObjectShape extends ShapeBase {
  type: 'node:foreignobject';
  use: Markup;
}

export interface WidgetShape extends ShapeBase {
  type: 'node:widget';
  use: ModelId;
}

export interface HTMLShape extends ShapeBase {
  type: 'node:html';
  use: Markup;
}

/**
 * A shape with no type, or with a type that no built-in shape has: the payload of a
 * custom view.
 */
export interface CustomShape extends ShapeBase {
  /**
   * @pattern ^(?!(edge|port|label|label:icon|node|node:(path|svg|round|diamond|comment|use|image|foreignobject|widget|html))$)
   */
  type?: string;
  use?: string;
  start?: string;
  end?: string;
}

/** A shape: its `type` selects the view and the type of its `use`. */
export type Shape =
  | EdgeShape
  | PortShape
  | LabelShape
  | IconShape
  | RectShape
  | PathShape
  | SVGShape
  | RoundShape
  | DiamondShape
  | CommentShape
  | UseShape
  | ImageShape
  | ForeignObjectShape
  | WidgetShape
  | HTMLShape
  | CustomShape;
/**
 * The shape of an element, typed as the variant that its view draws: sprotty selects
 * the view by the shape's `type`, so the view knows the variant.
 */
export function shapeOf<T extends Shape>(element?: {
  properties?: ElkProperties;
}): T | undefined {
  return element?.properties?.shape as T | undefined;
}

/**
 * The size of a comment's notch, limited to `width` and `height`. A notch that is
 * missing, not a number or negative draws the default of 15 pixels. 0 draws none.
 * ipyelk 2.x wrote the notch as a string, which this reads too.
 */
export function notchSize(
  use: NotchSize | string | undefined,
  width: number,
  height: number,
): number {
  const size = parseFloat(String(use));
  return Math.min(Number.isFinite(size) && size >= 0 ? size : 15, width, height);
}

export interface ElkProperties {
  cssClasses?: string;
  key?: string;
  hidden?: boolean;
  shape?: Shape;
  isSymbol?: boolean;
  selectable?: boolean;
  /**
   * Hover text rendered as the label's SVG `<title>`; typically the complete
   * text for a visually truncated label.
   */
  tooltip?: string;
  /**
   * render a full-width horizontal rule across the parent node just above
   * this label (e.g. a compartment header); opt-in, unset/false draws nothing
   */
  separator?: boolean;
  /**
   * Distance in SVG pixels between a separator and the top of its label.
   * Defaults to `1` when omitted.
   */
  separatorGap?: number;
}

export function isPrimitive(edge: ElkEdge): edge is ElkPrimitiveEdge {
  return (
    (edge as ElkPrimitiveEdge).source != null &&
    (edge as ElkPrimitiveEdge).target != null
  );
}

export function isExtended(edge: ElkEdge): edge is ElkExtendedEdge {
  return (
    (edge as ElkExtendedEdge).sources != null &&
    (edge as ElkExtendedEdge).targets != null
  );
}

export interface LayoutOptions {
  [key: string]: string;
}

export interface ElkPoint {
  x: number;
  y: number;
}

export interface ElkGraphElement {
  id?: string;
  labels?: ElkLabel[];
  properties?: ElkProperties;
  layoutOptions?: LayoutOptions;
}

export interface ElkShape extends ElkGraphElement {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

export interface ElkNode extends ElkShape {
  id: string;
  children?: ElkNode[];
  ports?: ElkPort[];
  edges?: ElkExtendedEdge[];
}

export interface ElkPort extends ElkShape {
  id: string;
}

export interface ElkLabel extends ElkShape {
  text?: string;
}

/**
 * @deprecated use ElkExtendedEdge directly
 */
export interface ElkEdge extends ElkGraphElement {
  id: string;
  junctionPoints?: ElkPoint[];
}

/**
 * @deprecated use ElkExtendedEdge instead
 */
export interface ElkPrimitiveEdge extends ElkEdge {
  source: string;
  sourcePort?: string;
  target: string;
  targetPort?: string;
  sourcePoint?: ElkPoint;
  targetPoint?: ElkPoint;
  bendPoints?: ElkPoint[];
}

export interface ElkExtendedEdge extends ElkEdge {
  sources: string[];
  targets: string[];
  sections?: ElkEdgeSection[];
}

export interface ElkEdgeSection extends ElkGraphElement {
  id: string;
  startPoint: ElkPoint;
  endPoint: ElkPoint;
  bendPoints?: ElkPoint[];
  incomingShape?: string;
  outgoingShape?: string;
  incomingSections?: string[];
  outgoingSections?: string[];
}

export interface ElkLayoutArguments {
  layoutOptions?: LayoutOptions;
  logging?: boolean;
  measureExecutionTime?: boolean;
}

export interface ElkCommonDescription {
  id?: string;
  name?: string;
  description?: string;
}

export interface ElkLayoutAlgorithmDescription extends ElkCommonDescription {
  category?: string;
  knownOptions?: string[];
  supportedFeatures?: string[];
}

export interface ElkLayoutOptionDescription extends ElkCommonDescription {
  group?: string;
  type?: string;
  targets?: string[];
}

export interface ElkLayoutCategoryDescription extends ElkCommonDescription {
  knownLayouters?: string[];
}

export interface ELK {
  layout(graph: ElkNode, args?: ElkLayoutArguments): Promise<ElkNode>;
  knownLayoutAlgorithms(): Promise<ElkLayoutAlgorithmDescription[]>;
  knownLayoutOptions(): Promise<ElkLayoutOptionDescription[]>;
  knownLayoutCategories(): Promise<ElkLayoutCategoryDescription[]>;
}

export interface ELKConstructorArguments {
  defaultLayoutOptions?: LayoutOptions;
  algorithms?: string[];
  workerUrl?: string;
  workerFactory?: (url?: string) => Worker;
}
