/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 * FIX BELOW FROM:
 */
import { SChildElementImpl, SModelRootImpl } from 'sprotty';

/**
 * Tests if the given model contains an id of then given element or one of its descendants.
 */
export function containsSome(
  root: SModelRootImpl,
  element: SChildElementImpl,
): boolean {
  const test = (element: SChildElementImpl) => root.index.getById(element.id) != null;
  const find = (elements: readonly SChildElementImpl[]): boolean =>
    elements.some((element) => test(element) || find(element.children));
  return find([element]);
}
