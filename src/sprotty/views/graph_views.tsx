import { injectable } from 'inversify';
import { svg, html } from 'snabbdom-jsx';
import { VNode } from 'snabbdom/vnode';
import { SGraph, IView, SParentElement } from 'sprotty';
import { ElkModelRenderer } from '../renderer';
// import { SDefsSchema } from '../json/elkgraph-to-sprotty';
const JSX = { createElement: html };


class SDefGraph extends SGraph{
  defs: SParentElement;
}
/**
 * IView component that turns an SGraph element and its children into a tree of virtual DOM elements.
 */
@injectable()
export class SGraphView implements IView {
  render(model: Readonly<SDefGraph>, context: ElkModelRenderer): VNode {
    const transform = `scale(${model.zoom}) translate(${-model.scroll.x},${-model.scroll
      .y})`;
    let graph = svg('svg', { class: { 'sprotty-graph': true } }, [
      svg('g', { transform: transform }, context.renderChildren(model)),
      svg('g', {class: {elkdefs:true}}, context.renderChildren(model.defs)),
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
