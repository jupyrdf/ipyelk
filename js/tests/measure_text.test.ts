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

describe('ELKTextSizerModel.reuse_sizes', () => {
  /** a sizer with the given state, and no widget manager */
  function sizer(state: Record<string, unknown>): any {
    const model: any = new (ELKTextSizerModel as any)();
    model.get = (key: string) => state[key];
    return model;
  }

  /** what `measure` does once the labels render at the given width */
  function measureAll(model: any, labels: any[], width: number): void {
    const box = { width, height: 10 };
    model.read_sizes(
      labels,
      labels.map(() => ({ innerHTML: '', getBoundingClientRect: () => box })),
    );
  }

  const label = (text: string, cssClasses = '', size = {}) => ({
    text,
    properties: { cssClasses },
    ...size,
  });

  it('measures a label again only if its text, its classes or the CSS change', () => {
    const state: Record<string, unknown> = {
      namespaced_css: '.a { font-size: 10px; }',
      _dom_classes: ['styled-widget-1'],
    };
    const model = sizer(state);

    const first = [label('a')];
    expect(model.reuse_sizes(first)).toEqual(first);
    measureAll(model, first, 20);

    // the kernel sends each label back as a new object, with its last size
    const a = label('a', '', { width: 20, height: 10 });
    const renamed = label('b', '', { width: 20, height: 10 });
    expect(model.reuse_sizes([a, renamed])).toEqual([renamed]);
    expect(a).toMatchObject({ width: 20, height: 10 });
    measureAll(model, [renamed], 30);

    const b = label('b');
    const restyled = label('a', 'bold');
    expect(model.reuse_sizes([b, restyled])).toEqual([restyled]);
    expect(b).toMatchObject({ width: 30, height: 10 });

    state.namespaced_css = '.a { font-size: 20px; }';
    const big = label('b');
    expect(model.reuse_sizes([big])).toEqual([big]);
    measureAll(model, [big], 40);
    expect(model.reuse_sizes([label('b')])).toEqual([]);

    // a style widget of another class can give the same CSS a new font
    state._dom_classes = ['styled-widget-2'];
    const styled = label('b');
    expect(model.reuse_sizes([styled])).toEqual([styled]);
  });

  it('keeps only the sizes of the last run', () => {
    const model = sizer({ namespaced_css: '', _dom_classes: [] });
    measureAll(model, model.reuse_sizes([label('a')]), 20);
    measureAll(model, model.reuse_sizes([label('b')]), 30);

    const back = [label('a')];
    expect(model.reuse_sizes(back)).toEqual(back);
  });

  it('measures again after the page loads a font', () => {
    const fonts = new EventTarget();
    vi.stubGlobal('document', { documentElement: {}, fonts });
    vi.stubGlobal('window', {
      getComputedStyle: () => ({ getPropertyValue: () => '' }),
    });
    const model = sizer({ namespaced_css: '', _dom_classes: [] });
    measureAll(model, model.reuse_sizes([label('a')]), 20);
    expect(model.reuse_sizes([label('a')])).toEqual([]);

    // the label was measured with the fallback font, while its web font loaded
    fonts.dispatchEvent(new Event('loadingdone'));
    const loaded = [label('a')];
    expect(model.reuse_sizes(loaded)).toEqual(loaded);
    measureAll(model, loaded, 25);
    const again = label('a');
    expect(model.reuse_sizes([again])).toEqual([]);
    expect(again).toMatchObject({ width: 25, height: 10 });
  });

  it('listens for font loads once, however many sizers and runs', () => {
    const fonts = new EventTarget();
    const listen = vi.spyOn(fonts, 'addEventListener');
    vi.stubGlobal('document', { documentElement: {}, fonts });
    vi.stubGlobal('window', {
      getComputedStyle: () => ({ getPropertyValue: () => '' }),
    });
    const models = [0, 1].map(() => sizer({ namespaced_css: '', _dom_classes: [] }));
    for (const model of models) {
      model.reuse_sizes([label('a')]);
      model.reuse_sizes([label('a')]);
    }
    expect(listen).toHaveBeenCalledOnce();
  });

  it('measures again after the font of the theme changes', () => {
    let fontSize = '13px';
    vi.stubGlobal('document', { documentElement: {} });
    vi.stubGlobal('window', {
      getComputedStyle: () => ({
        getPropertyValue: (name: string) =>
          name.endsWith('-size') ? fontSize : 'serif',
      }),
    });
    const model = sizer({ namespaced_css: '', _dom_classes: [] });
    measureAll(model, model.reuse_sizes([label('a')]), 20);
    expect(model.reuse_sizes([label('a')])).toEqual([]);

    fontSize = '20px';
    const bigger = [label('a')];
    expect(model.reuse_sizes(bigger)).toEqual(bigger);
  });

  it('measures again a label that measured 0', () => {
    const model = sizer({ namespaced_css: '', _dom_classes: [] });
    const first = [label('a')];
    model.reuse_sizes(first);
    model.read_sizes(first, [
      { getBoundingClientRect: () => ({ width: 0, height: 0 }) },
    ]);
    const again = [label('a')];
    expect(model.reuse_sizes(again)).toEqual(again);
  });

  it('keeps the size of a label with no text, which measures 0', () => {
    const model = sizer({ namespaced_css: '', _dom_classes: [] });
    const first = [label(''), { properties: { cssClasses: '' } }];
    expect(model.reuse_sizes(first)).toEqual(first);
    model.read_sizes(
      first,
      first.map(() => ({ getBoundingClientRect: () => ({ width: 0, height: 0 }) })),
    );
    const again = { properties: { cssClasses: '' } };
    expect(model.reuse_sizes([label(''), again])).toEqual([]);
    expect(again).toMatchObject({ width: 0, height: 0 });
  });

  it('answers without the DOM when every label has a size', () => {
    const model = sizer({ namespaced_css: '', _dom_classes: [] });
    measureAll(model, model.reuse_sizes([label('a')]), 20);

    const root = { id: 'root', children: [{ id: 'n', labels: [label('a')] }] };
    const outlet = { set: vi.fn(), save_changes: vi.fn() };
    const state: Record<string, unknown> = {
      namespaced_css: '',
      _dom_classes: [],
      inlet: { get: () => root },
      outlet,
    };
    model.get = (key: string) => state[key];

    // `document` does not exist here, so a measurement would throw
    expect(model.measure(3)).toBeNull();
    expect(root.children[0].labels[0]).toMatchObject({ width: 20, height: 10 });
    expect(outlet.set).toHaveBeenLastCalledWith(
      expect.objectContaining({
        gen: 3,
        value: expect.objectContaining({ id: 'root' }),
      }),
    );
    expect(outlet.save_changes).toHaveBeenCalledOnce();
  });
});
