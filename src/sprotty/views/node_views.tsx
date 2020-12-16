/**
 * Copyright (c) 2020 Dane Freeman.
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
import { VNode } from 'snabbdom/vnode';
import { IView, RectangularNodeView, setClass, getSubType } from 'sprotty';
import { ElkNode, ElkPort, ElkModelRenderer, ElkLabel } from '../sprotty-model';
// import { useCallback } from 'react';

const JSX = { createElement: snabbdom.svg };

@injectable()
export class ElkNodeView extends RectangularNodeView {
  render(node: ElkNode, context: ElkModelRenderer): VNode {
    let subtype = getSubType(node);

    console.log(subtype);

    let mark = this.renderMark(node, context);
    setClass(mark, 'elknode', true);
    setClass(mark, 'mouseover', node.hoverFeedback);
    setClass(mark, 'selected', node.selected);
    return (
      <g>
        {mark}
        {this.renderChildren(node, context)}
      </g>
    );
  }

  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let mark: VNode = (
      <rect x="0" y="0" width={node.bounds.width} height={node.bounds.height}></rect>
    );
    return mark;
  }

  renderChildren(node: ElkNode, context: ElkModelRenderer): VNode[] {
    return context.renderChildren(node);
  }
}

@injectable()
export class ElkUseNodeView extends ElkNodeView {
  renderMark(node: ElkNode, context: ElkModelRenderer): VNode {
    let use = node?.properties?.shape?.use;
    let href = context.hrefID(use);
    let mark: VNode = <use href={'#' + href} />;
    setClass(mark, use, true);
    return mark;
  }
}

@injectable()
export class ElkPortView extends RectangularNodeView {
  render(port: ElkPort, context: ElkModelRenderer): VNode {
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
          width={port.bounds.width}
          height={port.bounds.height}
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
export class ElkLabelView implements IView {
  render(label: ElkLabel, context: ElkModelRenderer): VNode {
    let mark: VNode;
    let use = label?.properties?.shape?.use;
    let href = context.hrefID(use);
    if (href) {
      console.warn('elklabel href', label);

      mark = <use class-elklabel={true} href={'#' + href} />;
      setClass(mark, use, true);
    } else {
      mark = <text class-elklabel={true}>{label.text}</text>;
    }

    return mark;
  }
}
