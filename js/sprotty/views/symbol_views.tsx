/** @jsx svg */
import { injectable } from 'inversify';
import { VNode } from 'snabbdom';
import { IView, svg } from 'sprotty';

import { ElkModelRenderer } from '../renderer';
import { ElkNode } from '../sprotty-model';

@injectable()
export class SymbolNodeView implements IView {
  render(symbol: ElkNode, context: ElkModelRenderer): VNode {
    let x = symbol.position?.x || 0;
    let y = symbol.position?.y || 0;
    let width = symbol.size.width || 0;
    let height = symbol.size.height || 0;
    let attrs = {
      class: {
        [symbol.id]: true,
        elksymbol: true,
      },
    };
    if (width && height) {
      attrs['viewBox'] = `${x} ${y} ${width} ${height}`;
    }
    return svg('symbol', attrs, ...context.renderChildren(symbol));
  }
}
