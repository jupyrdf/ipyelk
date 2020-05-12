/**
 * this exists for generating a complete JSON schema
 */
import * as ELK from 'elkjs';

export interface LazyElkEdge extends ELK.ElkEdge {
  sources: string[];
  targets: string[];
}

export type TAnyElkEdge =
  | ELK.ElkEdge
  | ELK.ElkExtendedEdge
  | ELK.ElkPrimitiveEdge
  | LazyElkEdge;

export interface AnyElkNode extends ELK.ElkNode {
  children?: AnyElkNode[];
  ports?: ELK.ElkPort[];
  edges?: TAnyElkEdge[];
  properties?: object;
}
