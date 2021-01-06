import { svg } from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { VNode } from 'snabbdom/vnode';
import { IView } from 'sprotty';
import { ElkNode } from '../sprotty-model';
import { ElkModelRenderer } from '../renderer';

// const JSX = { createElement: svg };

@injectable()
export class DefNodeView implements IView {
  render(def: ElkNode, context: ElkModelRenderer): VNode {
    let x = def.properties?.shape?.x || 0;
    let y = def.properties?.shape?.y || 0;
    let width = def.size.width || 0;
    let height = def.size.height || 0;
    // let viewbox = `${x} ${y} ${width} ${height}`
    // let vnode: VNode = <symbol viewBox={viewbox}>{context.renderChildren(def)}</symbol>;
    let attrs = {
      class: {
        [def.id]: true
      }
    };
    if (width && height) {
      attrs['viewBox'] = `${x} ${y} ${width} ${height}`;
    }
    return svg('symbol', attrs, context.renderChildren(def));
    // setClass(vnode, def.id, true);
    // return vnode;
  }
}
