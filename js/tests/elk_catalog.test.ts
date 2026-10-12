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

  it('lists the old ids that ELK still accepts', async () => {
    const { options } = await buildCatalog();
    const legacy = options.filter((o: { legacyIds?: string[] }) => o.legacyIds);
    // elkjs 0.12.0 has one: `layered.northOrSouthPort`
    expect(legacy.length).toBeGreaterThan(0);
    for (const option of legacy) {
      expect(option.legacyIds).not.toContain(option.id);
    }
  });
});
