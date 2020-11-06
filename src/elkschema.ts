/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
/**
 * this exists for generating a complete JSON schema
 */
import * as ELK from 'elkjs';

export interface LazyElkEdge extends ELK.ElkEdge {
  sources: string[];
  targets: string[];
}

export interface AnyElkPort extends ELK.ElkPort {
  properties?: object;
}

export type AnyElkEdge =
  | ELK.ElkEdge
  | ELK.ElkExtendedEdge
  | ELK.ElkPrimitiveEdge
  | LazyElkEdge;

export type AnyElkEdgeWithProperties = AnyElkEdge & { properties?: object };
export type AnyElkLabelWithProperties = ELK.ElkLabel & { properties?: object };

export interface AnyElkNode extends ELK.ElkNode {
  children?: AnyElkNode[];
  ports?: AnyElkPort[];
  edges?: AnyElkEdgeWithProperties[];
  properties?: object;
  labels?: AnyElkLabelWithProperties[];
}
