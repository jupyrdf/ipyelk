/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
/**
 * this exists for generating a complete JSON schema
 */
import * as ELK from 'elkjs';
import { ElkProperties } from './elkgraph-json';

export interface AnyElkLabelWithProperties extends ELK.ElkLabel {
  properties?: ElkProperties;
  labels?: AnyElkLabelWithProperties[];
}

export interface LazyElkEdge extends ELK.ElkEdge {
  sources: string[];
  targets: string[];
  labels?: AnyElkLabelWithProperties[];
}

export interface AnyElkPort extends ELK.ElkPort {
  properties?: ElkProperties;
  labels?: AnyElkLabelWithProperties[];
}

export type AnyElkEdge =
  | ELK.ElkEdge
  | ELK.ElkExtendedEdge
  | ELK.ElkPrimitiveEdge
  | LazyElkEdge;

export type AnyElkEdgeWithProperties = AnyElkEdge & { properties?: ElkProperties };

export interface AnyElkNode extends ELK.ElkNode {
  children?: AnyElkNode[];
  ports?: AnyElkPort[];
  edges?: AnyElkEdgeWithProperties[];
  properties?: ElkProperties;
  labels?: AnyElkLabelWithProperties[];
}
