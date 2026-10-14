/**
 * Copyright (c) 2026 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ELKTextSizerModel } from '../measure_text';

vi.mock('@jupyter-widgets/base', () => ({
  DOMWidgetModel: class {
    static serializers = {};
  },
  DOMWidgetView: class {},
  unpack_models: () => null,
}));
// the real module reads `window` on import
vi.mock('../tokens', () => ({
  ELK_CSS: {
    label: 'elklabel',
    widget_class: 'jp-ElkView',
    sizer_class: 'jp-ElkSizer',
  },
  ELK_DEBUG: false,
  NAME: '@jupyrdf/jupyter-elk',
  VERSION: '0.0.0',
}));

/** An element that records markup instead of parsing it: the tests run without a DOM. */
class FakeElement {
  readonly children: FakeElement[] = [];
  readonly classList = { add: (..._names: string[]) => undefined };
  readonly markup: string[] = [];
  textContent: string | null = null;

  constructor(readonly tagName: string) {}

  set innerHTML(html: string) {
    this.markup.push(html);
  }

  append(...nodes: FakeElement[]): void {
    this.children.push(...nodes);
  }

  appendChild(node: FakeElement): FakeElement {
    this.children.push(node);
    return node;
  }
}

function descendants(el: FakeElement): FakeElement[] {
  return [el, ...el.children.flatMap(descendants)];
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ELKTextSizerModel.make_container', () => {
  it('sets the namespaced CSS as the text of its style element, not as markup', () => {
    vi.stubGlobal('document', {
      createElement: (tag: string) => new FakeElement(tag),
      createElementNS: (_ns: string, tag: string) => new FakeElement(tag),
    });
    const css = '.a { fill: red; }</style><img src=x onerror="alert(1)"><style>';
    const state: Record<string, unknown> = {
      _dom_classes: ['styled-widget-1'],
      namespaced_css: css,
    };
    const model = Object.create(ELKTextSizerModel.prototype);
    model.get = (key: string) => state[key];

    const tree = descendants(model.make_container() as unknown as FakeElement);
    const styles = tree.filter((el) => el.tagName === 'style');
    expect(styles.map((el) => el.textContent)).toEqual([css]);
    expect(tree.flatMap((el) => el.markup)).toEqual([]);
    expect(tree.map((el) => el.tagName)).not.toContain('img');
  });
});
