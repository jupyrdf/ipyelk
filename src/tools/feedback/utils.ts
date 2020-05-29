import { SModelElement } from 'sprotty';

export function addCssClasses(root: SModelElement, cssClasses: string[]) {
  if (root.cssClasses == null) {
    root.cssClasses = [];
  }
  for (const cssClass of cssClasses) {
    if (root.cssClasses.indexOf(cssClass) < 0) {
      root.cssClasses.push(cssClass);
    }
  }
}

export function removeCssClasses(root: SModelElement, cssClasses: string[]) {
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
