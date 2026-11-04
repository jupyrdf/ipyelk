/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import ELK from 'elkjs/lib/elk.bundled';
import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';

it('lays out the Menagerie slider group in model order and routes its edge', async () => {
  // Read the options from the example so its configuration cannot drift from
  // this real-engine regression. Its widget payloads are removed before ELK.
  const notebook = JSON.parse(readFileSync('examples/12_Node_Menagerie.ipynb', 'utf8'));
  const source = notebook.cells
    .filter((cell: { cell_type: string }) => cell.cell_type === 'code')
    .map((cell: { source: string[] }) => cell.source.join(''))
    .find((code: string) => code.includes('def widget_example():'));
  const options: Record<string, string> = {};
  for (const [, key, value] of source.matchAll(/"([\w.]+)": "([\w]+)"/g)) {
    options[key] = value;
  }
  expect(options['considerModelOrder.strategy']).toBe('NODES_AND_EDGES');
  const graph = {
    id: 'root',
    layoutOptions: { 'org.eclipse.elk.hierarchyHandling': 'INCLUDE_CHILDREN' },
    children: [
      {
        id: 'sliders',
        layoutOptions: options,
        children: Array.from({ length: 5 }, (_, i) => ({
          id: String(i),
          width: 320,
          height: 40,
        })),
      },
      { id: 'slider_box', width: 320, height: 200 },
    ],
    edges: [{ id: 'edge', sources: ['sliders'], targets: ['slider_box'] }],
  };
  const result = await new ELK().layout(graph);
  const sliders = result.children!.find((node) => node.id === 'sliders')!;
  expect(sliders.children!.map((node) => node.id)).toEqual(['0', '1', '2', '3', '4']);
  const positions = sliders.children!.map((node) => node.y!);
  expect(positions.every((y, i) => i === 0 || y > positions[i - 1])).toBe(true);
  expect(result.edges![0].sections).toEqual([
    expect.objectContaining({
      startPoint: { x: expect.any(Number), y: expect.any(Number) },
      endPoint: { x: expect.any(Number), y: expect.any(Number) },
    }),
  ]);
});
