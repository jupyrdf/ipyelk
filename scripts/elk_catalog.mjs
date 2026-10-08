/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 *
 * Write the layout options, algorithms and categories that the installed elkjs
 * knows to `src/ipyelk/schema/elk-catalog.json`, sorted so that the output only
 * changes when elkjs does.
 */
import { writeFileSync } from 'node:fs';
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

/** the catalog of the installed elkjs, as a plain object */
export async function buildCatalog() {
  const elk = new ELK();
  const [options, algorithms, categories] = await Promise.all([
    elk.knownLayoutOptions(),
    elk.knownLayoutAlgorithms(),
    elk.knownLayoutCategories(),
  ]);
  return {
    elkjs: require('elkjs/package.json').version,
    options: options
      .map((o) => ({ ...o, targets: sorted(o.targets) }))
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
