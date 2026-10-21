/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 *
 * Bundles the render benchmark page (`index.html` + `entry.ts`) into
 * `build/bench-render/site`, from where `bench_render.py` serves it.
 */
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const here = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: here,
  base: './',
  logLevel: 'warn',
  build: {
    outDir: resolve(here, '../../build/bench-render/site'),
    emptyOutDir: true,
    target: 'es2020',
    minify: false,
    sourcemap: false,
    chunkSizeWarningLimit: 4000,
  },
});
