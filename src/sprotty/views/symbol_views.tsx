import { svg } from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { VNode } from 'snabbdom/vnode';
import { IView } from 'sprotty';
import { ElkNode } from '../sprotty-model';
import { ElkModelRenderer } from '../renderer';

// const JSX = { createElement: svg };

@injectable()
export class SymbolNodeView implements IView {
  render(symbol: ElkNode, context: ElkModelRenderer): VNode {
    let x = symbol.properties?.shape?.x || 0;
    let y = symbol.properties?.shape?.y || 0;
    let width = symbol.size.width || 0;
    let height = symbol.size.height || 0;
    let attrs = {
      class: {
        [symbol.id]: true,
        "elksymbol": true,
      }
    };
    if (width && height) {
      attrs['viewBox'] = `${x} ${y} ${width} ${height}`;
    }
    return svg('symbol', attrs, context.renderChildren(symbol));
  }
}
