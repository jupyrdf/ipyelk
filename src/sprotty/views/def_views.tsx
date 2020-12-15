import * as snabbdom from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { VNode } from 'snabbdom/vnode';
// import { h } from 'snabbdom';
import { IView, setClass } from 'sprotty';
import {
  DefNode,
  DefPath,
  DefCircle,
  ElkModelRenderer,
  DefEllipse,
  DefRect,
  DefRawSVG
} from '../sprotty-model';

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

@injectable()
export class DefPathView implements IView {
  render(def: DefPath, context: ElkModelRenderer): VNode {
    let segments = def.segments;
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    if (def.closed) {
      path += `Z`;
    }

    return <path d={path} />;
  }
}

@injectable()
export class DefCircleView implements IView {
  render(def: DefCircle, context: ElkModelRenderer): VNode {
    return <circle r={def.radius} />;
  }
}

@injectable()
export class DefEllipseView implements IView {
  render(def: DefEllipse, context: ElkModelRenderer): VNode {
    return <ellipse rx={def.rx} ry={def.ry} />;
  }
}

@injectable()
export class DefRectView implements IView {
  render(def: DefRect, context: ElkModelRenderer): VNode {
    return <rect width={def.width} height={def.height} />;
  }
}

@injectable()
export class DefRawSVGView implements IView {
  render(def: DefRawSVG, context: ElkModelRenderer): VNode {
    // let vnode: VNode = <g innerHTML={def.value}></g>;
    // let vnode: VNode = h("g", {props:{innerHTML: def.value}});
    let vnode: VNode = JSX.createElement('g', { props: { innerHTML: def.value } }, []);
    setClass(vnode, def.id, true);
    return vnode;
  }
}
