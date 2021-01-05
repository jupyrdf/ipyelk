/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import difference from 'lodash/difference';

import { Message } from '@phosphor/messaging';
import { Widget } from '@phosphor/widgets';
import { Signal } from '@phosphor/signaling';

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
// import { WidgetManager } from '@jupyter-widgets/jupyterlab-manager';
// import { ManagerBase } from '@jupyter-widgets/base';

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

import { NAME, VERSION, TAnyELKMessage, ELK_CSS } from '.';

import createContainer from './sprotty/di-config';
import { JLModelSource } from './sprotty/diagram-server';

import { NodeExpandTool, NodeSelectTool } from './tools';

import {
  IFeedbackActionDispatcher,
  FeedbackActionDispatcher
} from './tools/feedback/feedback-action-dispatcher';
import { ToolTYPES } from './tools/types';
import { PromiseDelegate } from '@phosphor/coreutils';

const DEFAULT_VALUE = { id: 'root' };
const POLL = 300;

export class ELKDiagramModel extends DOMWidgetModel {
  static model_name = 'ELKModel';

  layoutUpdated = new Signal<ELKDiagramModel, void>(this);

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKDiagramModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKDiagramView.view_name,
      _view_module_version: VERSION,
      value: DEFAULT_VALUE,
      defs: {},
      mark_layout: {},
      layouter: {}
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    this.on('change:value', this.value_changed, this);

    this.value_changed().catch(err => console.error(err));
  }

  async value_changed() {
    let rootNode = this.get('value');
    console.warn('layouting', rootNode);
    let layoutEngine: any = await this.layoutEngine(); // TODO need layoutEngine interface
    let result;
    if (layoutEngine) {
      result = await layoutEngine.layout(rootNode);
    } else {
      result = rootNode;
    }
    this.set('mark_layout', result);
  }

  async layoutEngine() {
    let mid = this.get('layouter').replace('IPY_MODEL_', '');
    return await this.widget_manager.get_model(mid);
  }
}

export class ELKDiagramView extends DOMWidgetView {
  static view_name = 'ELKDiagramView';

  model: ELKDiagramModel;
  source: JLModelSource;
  container: any;
  private div_id: string;
  toolManager: ToolManager;
  registry: ActionHandlerRegistry;
  actionDispatcher: ActionDispatcher;
  feedbackDispatcher: IFeedbackActionDispatcher;
  elementRegistry: SModelRegistry;
  was_shown = new PromiseDelegate<void>();

  initialize(parameters: any) {
    super.initialize(parameters);
    this.pWidget.addClass(ELK_CSS.widget_class);
  }

  async render() {
    const root = this.el as HTMLDivElement;
    const sprottyDiv = document.createElement('div');
    this.div_id = sprottyDiv.id = Private.next_id();

    root.appendChild(sprottyDiv);

    // don't bother initializing sprotty until actually on the page
    // schedule it
    this.initSprotty().catch(console.warn);
    this.wait_for_visible(true);
  }

  wait_for_visible = (initial = false) => {
    if (!this.pWidget.isVisible) {
      this.was_shown.resolve();
    } else {
      setTimeout(this.wait_for_visible, initial ? 0 : POLL);
    }
  };

  async initSprotty() {
    await this.was_shown.promise;
    // Create Sprotty viewer
    const container = createContainer(this.div_id, this);
    this.container = container;
    this.source = container.get<JLModelSource>(TYPES.ModelSource);
    this.source.widget_manager = this.model.widget_manager as any;
    this.elementRegistry = container.get(TYPES.SModelRegistry);
    this.toolManager = container.get<ToolManager>(TYPES.IToolManager);
    this.registry = container.get<ActionHandlerRegistry>(ActionHandlerRegistry);
    this.actionDispatcher = container.get<ActionDispatcher>(TYPES.IActionDispatcher);
    this.feedbackDispatcher = container.get<FeedbackActionDispatcher>(
      ToolTYPES.IFeedbackActionDispatcher
    );
    this.model.on('change:mark_layout', this.diagramLayout, this);
    this.model.on('change:selected', this.updateSelected, this);
    this.model.on('change:hovered', this.updateHover, this);
    this.model.on('change:interaction', this.interaction_mode_changed, this);
    this.model.on('msg:custom', this.handleMessage, this);
    this.model.on('change:defs', this.diagramLayout, this);
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

  resize = (width = -1, height = -1) => {
    if (width === -1 || height === -1) {
      const rect = (this.el as HTMLDivElement).getBoundingClientRect();
      width = rect.width;
      height = rect.height;
    }
    this.source.resize({ width, height, x: 0, y: 0 });
  };

  processPhosphorMessage(msg: Message): void {
    super.processPhosphorMessage(msg);
    switch (msg.type) {
      case 'resize':
        const resizeMessage = msg as Widget.ResizeMessage;
        let { width, height } = resizeMessage;
        this.resize(width, height);
        break;
      case 'after-show':
        this.resize();
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
    this.model.layoutUpdated.emit();
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
    let layout = this.model.get('mark_layout');
    let defs = this.model.get('defs');
    await this.source.updateLayout(layout, defs, this.div_id);
    this.model.layoutUpdated.emit();
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
