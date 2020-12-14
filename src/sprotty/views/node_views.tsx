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
import { IView, RectangularNodeView, setClass } from 'sprotty';
import { ElkNode, ElkPort, ElkModelRenderer, ElkLabel } from '../sprotty-model';
// import { useCallback } from 'react';

const JSX = { createElement: snabbdom.svg };

@injectable()
export class ElkNodeView extends RectangularNodeView {
  render(node: ElkNode, context: ElkModelRenderer): VNode {
    let mark: VNode;
    let href = context.hrefID(node.use);
    if (href) {
      mark = (
        <use
          class-elknode={true}
          class-mouseover={node.hoverFeedback}
          class-selected={node.selected}
          href={'#' + href}
        />
      );
      setClass(mark, node.use, true);
    } else {
      mark = (
        <rect
          class-elknode={true}
          class-mouseover={node.hoverFeedback}
          class-selected={node.selected}
          x="0"
          y="0"
          width={node.bounds.width}
          height={node.bounds.height}
        ></rect>
      );
    }
    return (
      <g>
        {mark}
        {context.renderChildren(node)}
      </g>
    );
  }
}

@injectable()
export class ElkPortView extends RectangularNodeView {
  render(port: ElkPort, context: ElkModelRenderer): VNode {
    let mark: VNode;
    let href = context.hrefID(port.use);
    if (href) {
      mark = (
        <use
          class-elkport={true}
          class-mouseover={port.hoverFeedback}
          class-selected={port.selected}
          href={'#' + href}
        />
      );
      setClass(mark, port.use, true);
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
    let href = context.hrefID(label.use);
    if (href) {
      console.warn('elklabel href', label);

      mark = <use class-elklabel={true} href={'#' + href} />;
      setClass(mark, label.use, true);
    } else {
      mark = <text class-elklabel={true}>{label.text}</text>;
    }

    return mark;
  }
}
