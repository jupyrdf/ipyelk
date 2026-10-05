/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import { CATALOG_PATH, buildCatalog } from '../../scripts/elk_catalog.mjs';

describe('elk-catalog.json', () => {
  it('matches the installed elkjs (run `pixi run build-py-elk-catalog`)', async () => {
    const committed = JSON.parse(readFileSync(CATALOG_PATH, 'utf-8'));
    expect(committed).toEqual(await buildCatalog());
  });
});
