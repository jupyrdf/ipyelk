/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // Match webpack's raw-loader CSS imports when testing the exporter itself.
  resolve: {
    alias: [{ find: /^!!raw-loader!(.*)$/, replacement: '$1?raw' }],
  },
  test: {
    environment: 'node',
    include: ['js/tests/**/*.test.ts'],
    globals: false,
  },
});
