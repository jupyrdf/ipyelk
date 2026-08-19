/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
export function isEnabled(value: unknown): boolean {
  return value == null ? true : Boolean(value);
}
