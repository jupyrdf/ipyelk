/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
/*******************************************************************************
 * Copyright (c) 2017 TypeFox GmbH (http://www.typefox.io) and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *******************************************************************************/
import * as snabbdom from 'snabbdom-jsx';
import { injectable } from 'inversify';
import { svg, html } from 'snabbdom-jsx';
import { VNode } from 'snabbdom/vnode';
import {
  ShapeView,
  RectangularNodeView,
  setClass,
  Point,
  ViewportRootElement,
  Dimension
  // HtmlRootView,
  // PreRenderedElement,
  // PreRenderedView,
  // ExpandButtonView,
  // IssueMarkerView,
  // RoutableView,
  // getSubType
  // IView
} from 'sprotty';
import { ElkNode, ElkPort, ElkLabel } from '../sprotty-model';
import { ElkModelRenderer } from '../renderer';
// import { useCallback } from 'react';

const JSX = { createElement: snabbdom.svg };

function svgStr(point: Point) {
  return `${point.x},${point.y}`;
}

@injectable()
export class ElkNodeView extends RectangularNodeView {
  render(node: ElkNode, context: ElkModelRenderer): VNode | undefined {
    if (!this.isDef(node) && !this.isVisible(node, context)) {
      return;
    }
    let mark = this.renderMark(node, context);
    if (!this.isDef(node)) {
      // skip marking extra classes on def nodes
      setClass(mark, 'elknode', true);
      setClass(mark, 'mouseover', node.hoverFeedback);
      setClass(mark, 'selected', node.selected);
    }

    setClass(mark, node.type, true);
    return (
      <g>
        {mark}
        <g class-elkchildren={true}>{this.renderChildren(node, context)}</g>
      </g>
    );
  }

  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let mark: VNode = (
      <rect x="0" y="0" width={node.size.width} height={node.size.height}></rect>
    );
    return mark;
  }

  renderChildren(node: ElkNode, context: ElkModelRenderer): VNode[] {
    return context.renderChildren(node);
  }

  /**
   *
   * @param node
   */
  isDef(node: ElkNode): boolean {
    return node?.properties?.isDef == true;
  }
}

@injectable()
export class ElkDiamondNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let width = node.size.width;
    let height = node.size.height;

    const top: Point = {
      x: width / 2,
      y: 0
    };

    const right: Point = {
      x: width,
      y: height / 2
    };

    const left: Point = {
      x: 0,
      y: height / 2
    };

    const bottom: Point = {
      x: width / 2,
      y: height
    };

    const points = `${svgStr(top)} ${svgStr(right)} ${svgStr(bottom)} ${svgStr(left)}`;
    return <polygon points={points} />;
  }
}

@injectable()
export class ElkRoundNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let rx = node.size.width / 2;
    let ry = node.size.height / 2;
    let x = node.properties?.shape?.x;
    if (x == undefined) x = rx;
    let y = node.properties?.shape?.y;
    if (y == undefined) y = ry;
    return <ellipse rx={rx} ry={ry} cx={x} cy={y} />;
  }
}

@injectable()
export class ElkImageNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let width = node.size.width;
    let height = node.size.height;
    return <image width={width} height={height} href={node.properties?.shape?.use} />;
  }
}

@injectable()
export class ElkCommentNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let tabSize = Number(node?.properties?.shape?.use) || 15;
    let width = node.size.width;
    let height = node.size.height;
    const points = [
      { x: 0, y: 0 },
      { x: width - tabSize, y: 0 },
      { x: width, y: tabSize },
      { x: width, y: height },
      { x: 0, y: height }
    ]
      .map(svgStr)
      .join(' ');

    return <polygon points={points} />;
  }
}

@injectable()
export class ElkPathNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let segments = node?.properties?.shape?.use;

    return <path d={segments} />;
  }
}

@injectable()
export class ElkUseNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let use = node?.properties?.shape?.use;
    let href = context.hrefID(use);
    let mark: VNode = (
      <use href={'#' + href} width={node.size.width} height={node.size.height} />
    );
    setClass(mark, use, true);
    return mark;
  }
}

@injectable()
export class ElkSVGNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let x = node.properties?.shape?.x;
    let y = node.properties?.shape?.y;
    return JSX.createElement(
      'g',
      {
        props: { innerHTML: node?.properties?.shape?.use },
        transform: `translate(${x} ${y})`
      },
      []
    );
  }
}

@injectable()
export class ElkCompartmentNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    if (node.parent.type == node.type) {
      const parentSize = (node.parent as any).size;
      return (
        <rect x="0" y="0" width={parentSize.width} height={node.size.height}></rect>
      );
    }
    return super.renderMark(node, context);
  }
}

@injectable()
export class ElkForeignObjectNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let contents = html(
      'div',
      { props: { innerHTML: node?.properties?.shape?.use } },
      []
    );
    return (
      <foreignObject
        requiredFeatures="http://www.w3.org/TR/SVG11/feature#Extensibility"
        height={node.size.height}
        width={node.size.width}
        x={0}
        y={0}
      >
        {contents}
      </foreignObject>
    );
  }
}

@injectable()
export class ElkHTMLNodeView extends ElkNodeView {
  render(node: ElkNode, context: ElkModelRenderer): VNode | undefined {
    if (!this.isDef(node) && !this.isVisible(node, context)) {
      return;
    }
    let mark = this.renderMark(node, context);
    if (!this.isDef(node)) {
      // skip marking extra classes on def nodes
      setClass(mark, 'elknode', true);
      setClass(mark, 'mouseover', node.hoverFeedback);
      setClass(mark, 'selected', node.selected);
    }

    setClass(mark, node.type, true);
    return svg(
      'g',
      {
        hook: {
          insert: vnode => context.overlayContent(vnode, node, true),
          destroy: vnode => context.overlayContent(vnode, node, false),
          update: (oldnode, vnode) =>
            context.overlayContent(vnode, node, this.isVisible(node, context))
        }
      },
      [mark, <g class-elkchildren={true}>{this.renderChildren(node, context)}</g>]
    );
  }
}

@injectable()
export class ElkPortView extends RectangularNodeView {
  render(port: ElkPort, context: ElkModelRenderer): VNode | undefined {
    let mark: VNode;
    let use = port?.properties?.shape?.use;
    let href = context.hrefID(use);
    if (href) {
      mark = (
        <use
          class-elkport={true}
          class-mouseover={port.hoverFeedback}
          class-selected={port.selected}
          href={'#' + href}
        />
      );
      setClass(mark, use, true);
    } else {
      mark = (
        <rect
          class-elkport={true}
          class-mouseover={port.hoverFeedback}
          class-selected={port.selected}
          // className={port.properties.classes}
          x="0"
          y="0"
          width={port.size.width}
          height={port.size.height}
        ></rect>
      );
    }
    return (
      <g>
        {mark}
        {context.renderChildren(port)}
      </g>
    );
  }
}

@injectable()
export class ElkLabelView extends ShapeView {
  render(label: ElkLabel, context: ElkModelRenderer): VNode | undefined {
    // label.root.zoom
    if (!this.isVisible(label, context)) {
      return undefined;
    }
    let mark: VNode;
    let use = label?.properties?.shape?.use;
    let href = context.hrefID(use);
    if (href) {
      mark = (
        <use
          class-elklabel={true}
          class-mouseover={label.hoverFeedback}
          class-selected={label.selected}
          href={'#' + href}
          width={label.size.width}
          height={label.size.height}
        />
      );
      setClass(mark, use, true);
    } else {
      mark = (
        <text class-elklabel={true} class-selected={label.selected} class-mouseover={label.hoverFeedback}>
          {label.text}
        </text>
      );
    }

    if (label.labels?.length) {
      let icon: ElkLabel = label.labels[0];
      let use = icon?.properties?.shape?.use;
      let href = context.hrefID(use);

      let height = label.size.height;

      let iconDims = this.dimension(icon);
      let labelDims = this.dimension(label);
      let iconPos: Point = {
        x: 0 + icon.position.x,
        y: (height - iconDims.height) / 2 + icon.position.x
      };
      let opts = icon?.layoutOptions || {};

      let spacing = Number(opts['org.eclipse.elk.spacing.labelLabel']) || 0;
      let labelPos: Point = {
        x: iconDims.width + spacing,
        y: (height - labelDims.height) / 2
      };
      mark = (
        <g>
          <use
            transform={`translate(${iconPos.x} ${iconPos.y})`}
            class-elklabel={true}
            class-mouseover={label.hoverFeedback}
            class-selected={label.selected}
            href={'#' + href}
            width={icon.size.width}
            height={icon.size.height}
          />
          <g transform={`translate(${labelPos.x} ${labelPos.y})`}>{mark}</g>
        </g>
      );
    }
    return mark;
  }

  dimension(label: ElkLabel): Dimension {
    return {
      width: label?.properties?.shape?.width || label.size.width,
      height: label?.properties?.shape?.height || label.size.height
    };
  }

  isVisible(label: ElkLabel, context: ElkModelRenderer): boolean {
    // check first if label is within bounding box of view
    let inView = super.isVisible(label, context);
    if (!inView) {
      return false;
    }
    // check if label should be rendered due to zoom level and min size
    let zoom = (label.root as ViewportRootElement).zoom;
    let heightLOD: boolean;
    if (label.size.height) {
      heightLOD = zoom * label.size.height > 3;
    } else {
      heightLOD = true;
    }
    return heightLOD;
  }
}
