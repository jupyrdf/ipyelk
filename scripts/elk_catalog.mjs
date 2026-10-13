/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 *
 * Write the layout options, algorithms and categories that the installed elkjs
 * knows to `src/ipyelk/schema/elk-catalog.json`, sorted so that the output only
 * changes when elkjs does.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ELK = require('elkjs/lib/elk.bundled.js');

export const CATALOG_PATH = fileURLToPath(
  new URL('../src/ipyelk/schema/elk-catalog.json', import.meta.url),
);

const byId = (a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
// some entries have no list at all: keep it missing
const sorted = (list) => list && [...list].sort();

/**
 * The old ids that ELK still accepts for an option, by option id.
 * `knownLayoutOptions()` leaves them out, so read the `$legacyIds(...)` calls in
 * the worker source. Fail if any call does not match, rather than miss one.
 */
function legacyIds() {
  const source = readFileSync(require.resolve('elkjs/lib/elk-worker.js'), 'utf-8');
  const calls = source.split('\n').filter((line) => line.includes('$legacyIds($'));
  // every use except `function $legacyIds(...)` itself
  if (calls.length !== source.split('$legacyIds(').length - 2) {
    throw new Error('a `$legacyIds(...)` call spans lines: update legacyIds()');
  }
  const found = {};
  for (const line of calls) {
    const id = line.match(/\(new LayoutOptionData\$Builder, '([^']+)'\)/);
    const old = line.match(/, \[('[\w.]+'(?:, '[\w.]+')*)\]\)+;$/);
    if (!id || !old) {
      throw new Error(`cannot read the legacy ids in: ${line.slice(0, 120)}`);
    }
    found[id[1]] = old[1].split(', ').map((quoted) => quoted.slice(1, -1));
  }
  return found;
}

/** the catalog of the installed elkjs, as a plain object */
export async function buildCatalog() {
  const elk = new ELK();
  const [options, algorithms, categories] = await Promise.all([
    elk.knownLayoutOptions(),
    elk.knownLayoutAlgorithms(),
    elk.knownLayoutCategories(),
  ]);
  const legacy = legacyIds();
  const lost = Object.keys(legacy).filter((id) => !options.some((o) => o.id === id));
  if (lost.length) {
    throw new Error(`legacy ids for options elkjs does not list: ${lost}`);
  }
  return {
    elkjs: require('elkjs/package.json').version,
    options: options
      .map((o) => ({
        ...o,
        targets: sorted(o.targets),
        legacyIds: sorted(legacy[o.id]),
      }))
      .sort(byId),
    algorithms: algorithms
      .map((a) => ({ ...a, knownOptions: sorted(a.knownOptions) }))
      .sort(byId),
    categories: categories
      .map((c) => ({ ...c, knownLayouters: sorted(c.knownLayouters) }))
      .sort(byId),
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const catalog = await buildCatalog();
  writeFileSync(CATALOG_PATH, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(`wrote ${catalog.options.length} options to ${CATALOG_PATH}`);
}
