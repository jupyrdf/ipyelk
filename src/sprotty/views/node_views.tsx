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
import { RenderingContext, IView, RectangularNodeView, SLabel } from 'sprotty';
import { ElkNode, ElkPort } from '../sprotty-model';

const JSX = { createElement: snabbdom.svg };

@injectable()
export class ElkNodeView extends RectangularNodeView {
  render(node: ElkNode, context: RenderingContext): VNode {
    return (
      <g>
        <rect
          class-elknode={true}
          class-mouseover={node.hoverFeedback}
          class-selected={node.selected}
          x="0"
          y="0"
          width={node.bounds.width}
          height={node.bounds.height}
        ></rect>
        {context.renderChildren(node)}
      </g>
    );
  }
}

@injectable()
export class ElkPortView extends RectangularNodeView {
  render(port: ElkPort, context: RenderingContext): VNode {
    return (
      <g>
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
        {context.renderChildren(port)}
      </g>
    );
  }
}

@injectable()
export class ElkLabelView implements IView {
  render(label: SLabel, context: RenderingContext): VNode {
    return <text class-elklabel={true}>{label.text}</text>;
  }
}
