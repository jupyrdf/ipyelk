/** @jsx html */
import { injectable } from 'inversify';
import { VNode } from 'snabbdom';
import { IView, SGraphImpl, SParentElementImpl, html, svg } from 'sprotty';

import { ElkModelRenderer } from '../renderer';

class SSymbolGraph extends SGraphImpl {
  symbols: SParentElementImpl;
}
/**
 * IView component that turns an SGraph element and its children into a tree of virtual DOM elements.
 */
@injectable()
export class SGraphView implements IView {
  render(model: Readonly<SSymbolGraph>, context: ElkModelRenderer): VNode {
    const transform = `scale(${model.zoom}) translate(${-model.scroll.x},${-model.scroll
      .y})`;
    let graph = svg(
      'svg',
      { class: { 'sprotty-graph': true } },
      svg('g', { transform: transform }, ...context.renderChildren(model)),
      svg(
        'g',
        { class: { elksymbols: true } },
        ...context.renderChildren(model.symbols),
      ),
    );
    const css_transform = {
      transform: `scale(${model.zoom}) translateZ(0) translate(${-model.scroll
        .x}px,${-model.scroll.y}px)`,
    };
    let overlay = (
      <div class-sprotty-overlay={true} style={css_transform}>
        {context.renderJLNodeWidgets()}
      </div>
    );
    let element: VNode = (
      <div class-sprotty-root={true}>
        <div class-sprotty-overlay={true}>{context.renderJLOverlayControl()}</div>
        {graph}
        {overlay}
      </div>
    );
    return element;
  }
}
