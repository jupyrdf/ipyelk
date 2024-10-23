/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { SModelElementImpl } from 'sprotty';

export function addCssClasses(root: SModelElementImpl, cssClasses: string[]) {
  if (root.cssClasses == null) {
    root.cssClasses = [];
  }
  for (const cssClass of cssClasses) {
    if (root.cssClasses.indexOf(cssClass) < 0) {
      root.cssClasses.push(cssClass);
    }
  }
}

export function removeCssClasses(root: SModelElementImpl, cssClasses: string[]) {
  if (root.cssClasses == null || root.cssClasses.length === 0) {
    return;
  }
  for (const cssClass of cssClasses) {
    const index = root.cssClasses.indexOf(cssClass);
    if (index !== -1) {
      root.cssClasses.splice(root.cssClasses.indexOf(cssClass), 1);
    }
  }
}
