/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { Container } from 'inversify';

import {
  ExportSvgPostprocessor,
  HiddenBoundsUpdater,
  IVNodePostprocessor,
  ModelRendererFactory,
  PatcherProvider,
  SModelRootImpl,
  TYPES,
  html,
} from 'sprotty';

/**
 * The decorations of sprotty's hidden render -- ids, CSS classes, positions,
 * edge label placement -- without the two that drive sprotty's own hidden
 * pipeline: `HiddenBoundsUpdater` collects every element until a `postUpdate`
 * that is never called here, and `ExportSvgPostprocessor` serves sprotty's
 * `RequestExportSvgAction`, which this export does not use.
 */
export function exportPostprocessors(container: Container): IVNodePostprocessor[] {
  if (!container.isBound(TYPES.HiddenVNodePostprocessor)) {
    return [];
  }
  return container
    .getAll<IVNodePostprocessor>(TYPES.HiddenVNodePostprocessor)
    .filter(
      (processor) =>
        !(processor instanceof HiddenBoundsUpdater) &&
        !(processor instanceof ExportSvgPostprocessor),
    );
}

/**
 * The whole diagram as SVG markup, rendered from the model.
 *
 * The live SVG holds what the view shows: culling leaves out what is off
 * screen, and the label view leaves out what is too small to read at the
 * current zoom. An export is neither, so the root is rendered again for the
 * `hidden` target -- no culling, no level of detail -- through the same views,
 * into a detached element that is dropped afterwards. The live DOM, its viewer
 * and the command stack take no part, so an export never shows up as a render
 * of the view. Returns `null` without a DOM.
 */
export function exportMarkup(
  container: Container,
  root: SModelRootImpl,
): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const factory = container.get<ModelRendererFactory>(TYPES.ModelRendererFactory);
  const renderer = factory('hidden', exportPostprocessors(container));
  const graph = renderer.renderElement(root);
  if (graph == null) {
    return null;
  }
  const patcher = container.get<PatcherProvider>(TYPES.PatcherProvider).patcher;
  const patched = patcher(document.createElement('div'), html('div', {}, graph));
  const svg = (patched.elm as Element | undefined)?.querySelector('svg');
  return svg == null ? null : svg.outerHTML;
}
