/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 * FIX BELOW FROM:
 */
import { SChildElement, SModelRoot } from 'sprotty';

/**
 * Tests if the given model contains an id of then given element or one of its descendants.
 */
export function containsSome(root: SModelRoot, element: SChildElement): boolean {
  const test = (element: SChildElement) => root.index.getById(element.id) !== undefined;
  const find = (elements: readonly SChildElement[]): boolean =>
    elements.some(element => test(element) || find(element.children));
  return find([element]);
}
