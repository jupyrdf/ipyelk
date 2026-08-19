/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { describe, expect, it } from 'vitest';

import { isEnabled } from './exporter_util';

describe('isEnabled', () => {
  it('is false when the stored value is false', () => {
    expect(isEnabled(false)).toBe(false);
  });
  it('is true when the stored value is true', () => {
    expect(isEnabled(true)).toBe(true);
  });
  it('defaults to true when unset (null/undefined)', () => {
    expect(isEnabled(null)).toBe(true);
    expect(isEnabled(undefined)).toBe(true);
  });
});
