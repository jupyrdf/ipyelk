/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 *
 * Drives the render benchmark page with Playwright, for machines where no
 * WebDriver browser launches. Playwright is not a dependency of this
 * repository: point NODE_PATH at an install of it, and CHROMIUM at a browser
 * (a Playwright `chrome-headless-shell` works), then:
 *
 *   node scripts/bench_render/playwright.mjs \
 *     --site build/bench-render --out build/bench-render/raw.json \
 *     --fixtures flat-1000,nested-1000 --rounds 5 --repeat 5 --zooms 1,0.25
 *   pixi run -e utest python scripts/bench_render.py --label x --results build/bench-render/raw.json
 *
 * Build the site first (`scripts/bench_render.py` does, or
 * `vite build --config scripts/bench_render/vite.config.mts`).
 */
import { readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { extname, join, resolve } from 'node:path';

// `require` honours NODE_PATH, which ES module resolution does not
const { chromium } = createRequire(import.meta.url)('playwright');

const args = Object.fromEntries(
  process.argv
    .slice(2)
    .map((arg, i, all) => (arg.startsWith('--') ? [arg.slice(2), all[i + 1]] : null))
    .filter(Boolean),
);
const site = resolve(args.site || 'build/bench-render');
const out = resolve(args.out || join(site, 'raw.json'));
const fixtures = (args.fixtures || 'flat-1000,nested-1000').split(',');
const query = new URLSearchParams({
  auto: '',
  fixtures: fixtures.map((name) => `../fixtures/${name}.json`).join(','),
  rounds: args.rounds || '5',
  repeat: args.repeat || '5',
  zooms: args.zooms || '1',
  ...(args.ops ? { ops: args.ops } : {}),
});

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
const server = createServer(async (req, res) => {
  try {
    const path = join(site, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    res.setHeader('content-type', TYPES[extname(path)] || 'application/json');
    res.end(await readFile(path));
  } catch (err) {
    res.statusCode = 404;
    res.end(String(err));
  }
});
await new Promise((ready) => server.listen(0, '127.0.0.1', ready));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM || undefined,
});
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  page.on('console', (msg) => msg.type() === 'error' && console.error(msg.text()));
  await page.goto(`${base}/site/index.html?${query}`);
  let seen = 0;
  for (;;) {
    const state = await page.evaluate(() => ({
      done: window.elkBenchResult != null,
      error: window.elkBenchError,
      log: window.elkBench?.log || [],
    }));
    for (const line of state.log.slice(seen)) console.error(`[bench] ${line}`);
    seen = state.log.length;
    if (state.error) throw new Error(state.error);
    if (state.done) break;
    await new Promise((tick) => setTimeout(tick, 1000));
  }
  const result = await page.evaluate(() => window.elkBenchResult);
  result.browser = `${browser.browserType().name()} ${browser.version()} (headless, playwright)`;
  await writeFile(out, JSON.stringify(result));
  console.error(`[bench] wrote ${out}`);
} finally {
  await browser.close();
  server.close();
}
