import { injectable } from 'inversify';
import { svg, html } from 'snabbdom-jsx';
import { VNode } from 'snabbdom/vnode';
import { SGraph, IView } from 'sprotty';
import { ElkModelRenderer } from '../sprotty-model';
// import {} from "snabbdom-style";
// import * as snabbdom from "snabbdom-jsx";
const JSX = { createElement: html };

/**
 * IView component that turns an SGraph element and its children into a tree of virtual DOM elements.
 */
@injectable()
export class SGraphView implements IView {
  render(model: Readonly<SGraph>, context: ElkModelRenderer): VNode {
    const transform = `scale(${model.zoom}) translate(${-model.scroll.x},${-model.scroll
      .y})`;
    let graph = svg('svg', { class: { 'sprotty-graph': true } }, [
      svg('g', { transform: transform }, context.renderChildren(model))
    ]);
    const css_transform = {
      transform: `scale(${model.zoom}) translate(${-model.scroll.x}px,${-model.scroll
        .y}px)`
    };
    let overlay = (
      <div class-sprotty-overlay={true} style={css_transform}>
        {context.renderWidgets()}
      </div>
    );
    return (
      <div class-sprotty-root={true}>
        {graph}
        {overlay}
      </div>
    );
  }
}
