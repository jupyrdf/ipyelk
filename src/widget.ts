/**
 * Copyright (c) 2020 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import difference from 'lodash/difference';

import { Message } from '@phosphor/messaging';
import { Widget } from '@phosphor/widgets';

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';

import Worker from '!!worker-loader!elkjs/lib/elk-worker.min.js';
import * as ELK from 'elkjs/lib/elk-api';

import {
  Action,
  ActionDispatcher,
  ActionHandlerRegistry,
  HoverFeedbackAction,
  SelectAction,
  SelectionResult,
  SModelRegistry,
  ToolManager,
  TYPES
} from 'sprotty';

import { NAME, VERSION, ELK_DEBUG, TAnyELKMessage } from '.';

import createContainer from './sprotty/di-config';
import { JLModelSource } from './sprotty/diagram-server';

import { NodeExpandTool, NodeSelectTool } from './tools';

import {
  IFeedbackActionDispatcher,
  FeedbackActionDispatcher
} from './tools/feedback/feedback-action-dispatcher';
import { ToolTYPES } from './tools/types';
import { ELKTextSizerModel, ELKTextSizerView } from './measure_text';
export { ELKTextSizerModel, ELKTextSizerView };

const WIDGET_CLASS = 'jp-ElkView';
const DEFAULT_VALUE = { id: 'root' };

export class ELKModel extends DOMWidgetModel {
  static model_name = 'ELKModel';

  protected _elk: ELK.ELK;

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKView.view_name,
      _view_module_version: VERSION,
      value: DEFAULT_VALUE,
      _mark_layout: {}
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    this.on('change:value', this.value_changed, this);
    this.on('change:_view_count', this.view_count_changed, this);
    if (this.get('_view_count') == null) {
      this.set('_view_count', 0);
    }
    this.value_changed().catch(err => console.error(err));
  }

  async view_count_changed() {
    const viewCount: number = this.get('_view_count') || 0;
    ELK_DEBUG && console.warn('ELK model', this.cid, 'has', viewCount, 'views');
    const elk: any = this._elk;
    if (viewCount && elk == null) {
      await this.value_changed();
    } else if (viewCount <= 0 && elk) {
      this.cullElk();
    }
  }

  protected cullElk() {
    const elk: any = this._elk;
    if (elk != null) {
      ELK_DEBUG && console.warn('ELK worker culling for', this.cid);
      elk.worker?.terminate();
    } else {
      ELK_DEBUG && console.warn('ELK was already culled for', this.cid);
    }
    this._elk = null;
  }

  protected ensureElk() {
    if (this._elk == null) {
      this._elk = new ELK.default({
        workerFactory: () => {
          ELK_DEBUG && console.warn('ELK Worker created');
          return new (Worker as any)();
        }
      } as any);
    }
  }

  async value_changed() {
    if ((this.get('_view_count') || 0) <= 0) {
      this.cullElk();
      return;
    }

    const value = this.get('value');
    this.ensureElk();
    this.set('_mark_layout', await this._elk.layout(value));
  }
}

export class ELKView extends DOMWidgetView {
  static view_name = 'ELKView';

  model: ELKModel;
  source: JLModelSource;
  container: any;
  private div_id: string;
  toolManager: ToolManager;
  registry: ActionHandlerRegistry;
  actionDispatcher: ActionDispatcher;
  feedbackDispatcher: IFeedbackActionDispatcher;
  elementRegistry: SModelRegistry;

  initialize(parameters: any) {
    super.initialize(parameters);
    this.pWidget.addClass(WIDGET_CLASS);
  }

  async render() {
    // don't bother initializing sprotty until actually on the page
    this.once('displayed', this.initSprotty, this);
  }

  initSprotty() {
    const root = this.el as HTMLDivElement;
    const sprottyDiv = document.createElement('div');
    this.div_id = sprottyDiv.id = Private.next_id();

    root.appendChild(sprottyDiv);

    // Create Sprotty viewer
    const container = createContainer(this.div_id, this);
    this.container = container;
    this.source = container.get<JLModelSource>(TYPES.ModelSource);
    this.elementRegistry = container.get(TYPES.SModelRegistry);
    this.toolManager = container.get<ToolManager>(TYPES.IToolManager);
    this.registry = container.get<ActionHandlerRegistry>(ActionHandlerRegistry);
    this.actionDispatcher = container.get<ActionDispatcher>(TYPES.IActionDispatcher);
    this.feedbackDispatcher = container.get<FeedbackActionDispatcher>(
      ToolTYPES.IFeedbackActionDispatcher
    );
    this.model.on('change:_mark_layout', this.diagramLayout, this);
    this.model.on('change:selected', this.updateSelected, this);
    this.model.on('change:hovered', this.updateHover, this);
    this.model.on('change:interaction', this.interaction_mode_changed, this);
    this.model.on('msg:custom', this.handleMessage, this);
    this.touch(); //to sync back the diagram state

    // Register Action Handlers
    this.registry.register(SelectAction.KIND, this);
    this.registry.register(SelectionResult.KIND, this); //sprotty complains if doesn't have a SelectionResult handler
    this.registry.register(HoverFeedbackAction.KIND, this);

    // Register Tools
    this.toolManager.registerDefaultTools(
      container.resolve(NodeSelectTool),
      container.resolve(NodeExpandTool)
    );
    this.toolManager.enableDefaultTools();

    this.diagramLayout().catch(err =>
      console.warn('ELK Failed initial view render', err)
    );
  }

  processPhosphorMessage(msg: Message): void {
    super.processPhosphorMessage(msg);
    switch (msg.type) {
      case 'resize':
        const resizeMessage = msg as Widget.ResizeMessage;
        let { width, height } = resizeMessage;
        if (width === -1 || height === -1) {
          const rect = (this.el as HTMLDivElement).getBoundingClientRect();
          width = rect.width;
          height = rect.height;
        }
        this.source.resize({ width, height, x: 0, y: 0 });
        break;
    }
  }

  handle(action: Action) {
    switch (action.kind) {
      case SelectAction.KIND:
        this.source.getSelected().then(ids => {
          this.model.set('selected', ids);
          this.touch();
        });
      case SelectionResult.KIND:
        break;
      case HoverFeedbackAction.KIND:
        let hoverFeedback: HoverFeedbackAction = action as HoverFeedbackAction;
        if (hoverFeedback.mouseIsOver) {
          this.model.set('hovered', hoverFeedback.mouseoverElement);
          this.touch();
        }
        break;
      default:
        break;
    }
  }

  /**
   * Dictionary of events and handlers
   */
  events(): { [e: string]: string } {
    return { click: '_handle_click' };
  }

  /**
   * Handles when the button is clicked.
   */
  _handle_click(event) {
    // event.preventDefault();
    this.send({ event: 'click', id: this.model.get('hovered') });
  }

  updateSelected() {
    let selected: string[] = this.model.get('selected');
    let old_selected: string[] = this.model.previous('selected');
    let exiting: string[] = difference(old_selected, selected);
    let entering: string[] = difference(selected, old_selected);
    this.actionDispatcher.dispatch(new SelectAction(entering, exiting));
  }

  updateHover() {
    let hovered: string = this.model.get('hovered');
    let old_hovered: string = this.model.previous('hovered');
    this.actionDispatcher.dispatchAll([
      new HoverFeedbackAction(hovered, true),
      new HoverFeedbackAction(old_hovered, false)
    ]);
  }

  async interaction_mode_changed() {
    // let interaction = this.model.get('interaction');
    // console.log('interaction ', interaction);
  }

  async diagramLayout() {
    let layout = this.model.get('_mark_layout');
    await this.source.updateLayout(layout);
  }

  normalizeElementIds(model_id: string | string[] | null) {
    let elementIds: string[] = [];
    if (model_id != null) {
      if (!Array.isArray(model_id)) {
        elementIds = [model_id];
      } else {
        elementIds = model_id;
      }
    }
    return elementIds;
  }

  handleMessage(content: TAnyELKMessage) {
    switch (content.action) {
      case 'center':
        this.source.center(
          this.normalizeElementIds(content.model_id),
          content.animate,
          content.retain_zoom
        );
        break;
      case 'fit':
        this.source.fit(
          this.normalizeElementIds(content.model_id),
          content.padding == null ? 0 : content.padding,
          content.max_zoom == null ? Infinity : content.max_zoom,
          content.animate == null ? true : content.animate
        );
        break;
      default:
        console.warn('ELK unhandled message', content);
        break;
    }
  }
}

namespace Private {
  let _next_id = 0;
  export function next_id() {
    return `sprotty_${_next_id++}`;
  }
}
