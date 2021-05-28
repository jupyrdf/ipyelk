/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import difference from 'lodash/difference';

import { Message } from '@lumino/messaging';
import { Widget } from '@lumino/widgets';
import { Signal } from '@lumino/signaling';

import {
  DOMWidgetModel,
  DOMWidgetView,
  unpack_models as deserialize
} from '@jupyter-widgets/base';
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

import { NAME, VERSION, TAnyELKMessage, ELK_CSS } from './tokens';

import createContainer from './sprotty/di-config';
import { JLModelSource } from './sprotty/diagram-server';

import { NodeExpandTool, NodeSelectTool } from './tools';

import {
  IFeedbackActionDispatcher,
  FeedbackActionDispatcher
} from './tools/feedback/feedback-action-dispatcher';
import { ToolTYPES } from './tools/types';
import { PromiseDelegate } from '@lumino/coreutils';

const POLL = 300;

export class ELKViewerModel extends DOMWidgetModel {
  static model_name = 'ELKViewerModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    source: { deserialize },
    selection: { deserialize },
    hover: { deserialize },
    painter: { deserialize },
    zoom: { deserialize },
    pan: { deserialize }
  };
  layoutUpdated = new Signal<ELKViewerModel, void>(this);
  diagramUpdated = new Signal<ELKViewerModel, void>(this);

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKViewerModel.model_name,
      _model_module_version: VERSION,
      _view_module: NAME,
      _view_name: ELKViewerView.view_name,
      _view_module_version: VERSION,
      symbols: {},
      source: null
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
  }
}

export class ELKViewerView extends DOMWidgetView {
  static view_name = 'ELKViewerView';

  model: ELKViewerModel;
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
    this.on('change:source', this.on_source_changed, this);
    this.on_source_changed();
  }
  async on_source_changed() {
    // TODO disconnect old ones
    let source = this.model.get('source');
    if (source) {
      source.on('change:value', this.diagramLayout, this);
      this.diagramLayout();
    }
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
    // this.model.on('change:mark_layout', this.diagramLayout, this);
    this.model.on('change:selection', this.updateSelectedTool, this);
    this.model.on('change:hover', this.updateHoverTool, this);
    this.model.on('change:interaction', this.interaction_mode_changed, this);
    this.model.on('msg:custom', this.handleMessage, this);
    this.model.on('change:symbols', this.diagramLayout, this);

    // init for the first time
    this.updateSelectedTool();
    this.updateHoverTool();

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
          let selection = this.model.get('selection');
          if (selection != null) {
            selection.set('ids', ids);
            selection.save_changes();
            this.model.diagramUpdated.emit(void 0);
          }
        });
        break;
      case SelectionResult.KIND:
        break;
      case HoverFeedbackAction.KIND:
        let hoverFeedback: HoverFeedbackAction = action as HoverFeedbackAction;
        if (hoverFeedback.mouseIsOver) {
          let hover = this.model.get('hover');
          if (hover != null) {
            hover.set('ids', hoverFeedback.mouseoverElement);
            hover.save_changes();
            this.model.diagramUpdated.emit(void 0);
          }
        }
        break;
      default:
        break;
    }
  }

  updateSelectedTool() {
    let selection = this.model.get('selection');
    if (selection != null) {
      selection.on('change:ids', this.updateSelected, this);
    }
  }
  async updateSelected() {
    let selection = this.model.get('selection');
    if (selection != null) {
      let selected: string[] = selection.get('ids');
      let old_selected: string[] = selection.previous('ids');
      let exiting: string[] = difference(old_selected, selected);
      let entering: string[] = difference(selected, old_selected);
      await this.actionDispatcher.dispatch(new SelectAction(entering, exiting));
      this.model.diagramUpdated.emit(void 0);
    }
  }

  updateHoverTool() {
    let hover = this.model.get('hover');
    if (hover != null) {
      hover.on('change:ids', this.updateHover, this);
    }
  }

  async updateHover() {
    let hover = this.model.get('hover');
    if (hover != null) {
      let hovered: string = hover.get('ids');
      let old_hovered: string = hover.previous('ids');
      await this.actionDispatcher.dispatchAll([
        new HoverFeedbackAction(hovered, true),
        new HoverFeedbackAction(old_hovered, false)
      ]);
      this.model.diagramUpdated.emit(void 0);
    }
  }

  async interaction_mode_changed() {
    // let interaction = this.model.get('interaction');
  }

  async diagramLayout() {
    let layout = this.model.get('source')?.get('value');
    let symbols = this.model.get('symbols');
    if (layout == null || symbols == null || this.source == null) {
      // bailing
      return null;
    }
    await this.source.updateLayout(layout, symbols, this.div_id);
    this.model.layoutUpdated.emit();
    this.model.diagramUpdated.emit();
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
