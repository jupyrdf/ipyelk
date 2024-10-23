/**
 * Copyright (c) 2024 ipyelk contributors.
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

export interface AnyElkEdgeWithProperties extends ELK.ElkExtendedEdge {
  sources: string[];
  targets: string[];
  labels?: AnyElkLabelWithProperties[];
  properties?: ElkProperties;
}

export interface AnyElkPort extends ELK.ElkPort {
  properties?: ElkProperties;
  labels?: AnyElkLabelWithProperties[];
}

export interface AnyElkNode extends ELK.ElkNode {
  children?: AnyElkNode[];
  ports?: AnyElkPort[];
  edges?: AnyElkEdgeWithProperties[];
  properties?: ElkProperties;
  labels?: AnyElkLabelWithProperties[];
}
