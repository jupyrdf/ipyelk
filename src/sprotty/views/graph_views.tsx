import { injectable } from 'inversify';
import { svg, html } from 'snabbdom-jsx';
import { VNode } from 'snabbdom/vnode';
import { SGraph, IView, SParentElement } from 'sprotty';
import { ElkModelRenderer } from '../renderer';
const JSX = { createElement: html };

class SSymbolGraph extends SGraph {
  symbols: SParentElement;
}
/**
 * IView component that turns an SGraph element and its children into a tree of virtual DOM elements.
 */
@injectable()
export class SGraphView implements IView {
  render(model: Readonly<SSymbolGraph>, context: ElkModelRenderer): VNode {
    const transform = `scale(${model.zoom}) translate(${-model.scroll.x},${-model.scroll
      .y})`;
    let graph = svg('svg', { class: { 'sprotty-graph': true } }, [
      svg('g', { transform: transform }, context.renderChildren(model)),
      svg('g', { class: { elksymbols: true } }, context.renderChildren(model.symbols))
    ]);
    const css_transform = {
      transform: `scale(${model.zoom}) translateZ(0) translate(${-model.scroll
        .x}px,${-model.scroll.y}px)`
    };
    let overlay = (
      <div class-sprotty-overlay={true} style={css_transform}>
        {context.renderJLNodeWidgets()}
      </div>
    );
    return (
      <div class-sprotty-root={true}>
        <div class-sprotty-overlay={true}>{context.renderJLOverlayControl()}</div>
        {graph}
        {overlay}
      </div>
    );
  }
}
