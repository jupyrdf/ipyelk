/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { ElkNode } from './sprotty/json/elkgraph-json';
import { modelIds } from './viewport_util';

/**
 * Ids that frame the whole diagram: every element of the laid-out ELK JSON, since
 * sprotty frames each id by its own bounds (nodes, ports and labels; not edge
 * routes), and ports and labels can sit outside their parent's. Naming them, rather
 * than fitting with no ids, frames the whole diagram even when something is
 * selected. Empty while no top-level node has a size, i.e. before ELK has laid
 * anything out.
 */
export function fitTargets(layout: ElkNode | null | undefined): string[] {
  const nodes = layout?.children || [];
  if (!nodes.some((node) => node.width > 0 && node.height > 0)) {
    return [];
  }
  return [...modelIds(layout)];
}

/** What `FirstFit` needs from the view it fits. */
export interface IFirstFitHost {
  /** The kernel's `Viewer.fit_on_first_layout`. */
  isEnabled(): boolean;
  /** Whether the view has a size on the page, so a fit has a canvas to fill. */
  isShown(): boolean;
  /** Fit these ids, without animation. */
  fit(ids: string[]): void;
  /** Start calling `revealed()` when the view may have been shown. */
  watch(): void;
  /** Stop calling `revealed()`. */
  unwatch(): void;
}

/**
 * One view's fit after its first layout (`Viewer.fit_on_first_layout`).
 *
 * The first layout with something to frame decides: a shown view fits at once, and
 * a hidden one (in a collapsed accordion, a background tab, ...) fits the first
 * time it is revealed, since sprotty cannot fit an empty canvas. Either way the fit
 * happens once per view, so later layouts and reveals keep the user's camera.
 *
 * `state` is `layout` until that first layout, `reveal` while a hidden view waits,
 * and `done` after the fit, or when there is none to do.
 */
export class FirstFit {
  state: 'layout' | 'reveal' | 'done' = 'layout';
  private targets: string[] = [];
  private watching = false;

  constructor(private readonly host: IFirstFitHost) {}

  /** Call after each rendered layout. */
  afterLayout(layout: ElkNode | null | undefined): void {
    if (this.state === 'done') {
      return;
    }
    const targets = fitTargets(layout);
    if (!targets.length) {
      return; // nothing laid out yet: the next layout is still the first
    }
    this.targets = targets;
    if (this.state === 'layout') {
      if (!this.host.isEnabled()) {
        this.state = 'done';
        return;
      }
      this.state = 'reveal';
    }
    this.revealed();
    if (this.state === 'reveal' && !this.watching) {
      this.watching = true;
      this.host.watch();
    }
  }

  /** Call when the view may have been shown or resized. */
  revealed(): void {
    if (this.state !== 'reveal' || !this.host.isShown()) {
      return;
    }
    const enabled = this.host.isEnabled();
    this.finish();
    if (enabled) {
      this.host.fit(this.targets);
    }
  }

  /**
   * An explicit camera (`set_viewport`) supersedes a fit still waiting for a
   * reveal. Before the first layout there is nothing to keep: the first model
   * brings its own camera.
   */
  cancel(): void {
    if (this.state === 'reveal') {
      this.finish();
    }
  }

  dispose(): void {
    this.cancel();
    this.state = 'done';
  }

  private finish(): void {
    this.state = 'done';
    if (this.watching) {
      this.watching = false;
      this.host.unwatch();
    }
  }
}

/**
 * The `IFirstFitHost` of a view rendered in `element()`: shown while it has a size on the
 * page, and watched with a `ResizeObserver`, which also sees a CSS reveal
 * (`display: none` lifted) that sends the view no lumino message.
 */
export function elementFirstFitHost(
  element: () => HTMLElement,
  isEnabled: () => boolean,
  fit: (ids: string[]) => void,
  revealed: () => void,
): IFirstFitHost {
  let observer: ResizeObserver | null = null;
  return {
    isEnabled,
    fit,
    isShown: () => {
      const el = element();
      const { width, height } = el.getBoundingClientRect();
      return el.isConnected && width > 0 && height > 0;
    },
    watch: () => {
      if (observer == null && typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(() => revealed());
        observer.observe(element());
      }
    },
    unwatch: () => {
      observer?.disconnect();
      observer = null;
    },
  };
}
