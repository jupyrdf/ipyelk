/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import { CATALOG_PATH, buildCatalog } from '../../scripts/elk_catalog.mjs';

const REGENERATE = 'run `pixi run build-py-elk-catalog` and commit elk-catalog.json';

describe('elk-catalog.json', () => {
  it('matches the installed elkjs (run `pixi run build-py-elk-catalog`)', async () => {
    const committed = JSON.parse(readFileSync(CATALOG_PATH, 'utf-8'));
    // a round trip drops the `undefined` lists that JSON leaves out
    const installed = JSON.parse(JSON.stringify(await buildCatalog()));
    expect(committed.elkjs, `elkjs changed: ${REGENERATE}`).toBe(installed.elkjs);
    expect(committed, `the catalog is stale: ${REGENERATE}`).toEqual(installed);
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
