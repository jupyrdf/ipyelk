import * as snabbdom from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { VNode } from 'snabbdom/vnode';
import { RenderingContext, IView } from 'sprotty';
import { DefNode, DefPath } from '../sprotty-model';

const JSX = { createElement: snabbdom.svg };

export class DefElement {
  x: number;
  y: number;

  render(): VNode | undefined {
    return;
  }
}

export class Path extends DefElement {
  points: [number, number][];
  render(): VNode {
    return <path />;
  }
}

export class Circle extends DefElement {}

export class Rect extends DefElement {}

@injectable()
export class DefNodeView implements IView {
  render(def: DefNode, context: RenderingContext): VNode {
    console.log('defnodeview', def);
    return (
      // this is what needs to have the proper element id
      <g>{context.renderChildren(def)}</g>
    );
  }
}

@injectable()
export class DefsNodeView implements IView {
  render(def: DefNode, context: RenderingContext): VNode {
    console.log(def);
    return <defs>{context.renderChildren(def)}</defs>;
  }
}

@injectable()
export class DefPathView implements IView {
  render(def: DefPath, context: RenderingContext): VNode {
    console.log('defpathview', def);
    let segments = def.segments;
    const firstPoint = segments[0];
    let path = `M ${firstPoint.x},${firstPoint.y}`;
    for (let i = 1; i < segments.length; i++) {
      const p = segments[i];
      path += ` L ${p.x},${p.y}`;
    }
    if (def.closed){
      path += `Z`;
    }


    return <path d={path} />;
  }
}
