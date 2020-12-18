import * as snabbdom from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { VNode } from 'snabbdom/vnode';
// import { h } from 'snabbdom';
import { IView, setClass } from 'sprotty';
import { DefNode, ElkModelRenderer } from '../sprotty-model';

const JSX = { createElement: snabbdom.svg };

@injectable()
export class DefsNodeView implements IView {
  render(def: DefNode, context: ElkModelRenderer): VNode {
    return <defs>{context.renderChildren(def)}</defs>;
  }
}

@injectable()
export class DefNodeView implements IView {
  render(def: DefNode, context: ElkModelRenderer): VNode {
    let vnode: VNode = <g>{context.renderChildren(def)}</g>;
    setClass(vnode, def.id, true);
    return vnode;
  }
}
