/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */

/**
 * What changed between the selection a view already shows and one it was told
 * about.
 *
 * Selection is a SET: `ids` arriving in a different order is not a change. Two
 * views of one diagram model each observe `change:ids` and each write the ids
 * back from their own sprotty index, so treating a reordering as a change makes
 * them dispatch `SelectAction`s at each other forever -- which pegs the
 * renderer and eventually runs the browser out of memory.
 */
export function selectionDelta(
  current: string[] | undefined | null,
  next: string[] | undefined | null,
): { entering: string[]; exiting: string[]; changed: boolean } {
  const currentSet = new Set(current || []);
  const nextSet = new Set(next || []);
  const entering = [...nextSet].filter((id) => !currentSet.has(id));
  const exiting = [...currentSet].filter((id) => !nextSet.has(id));
  return { entering, exiting, changed: entering.length > 0 || exiting.length > 0 };
}

/**
 * Canonical form for a selection written back to the kernel: sorted, so the
 * value does not depend on which view gathered it, and de-duplicated.
 */
export function canonicalSelection(ids: string[] | undefined | null): string[] {
  return [...new Set(ids || [])].sort();
}
