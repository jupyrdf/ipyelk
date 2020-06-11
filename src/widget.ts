import 'reflect-metadata';
import difference from 'lodash/difference';

import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
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

import Worker from '!!worker-loader!elkjs/lib/elk-worker.min.js';
import { NAME, VERSION } from '.';

import createContainer from './sprotty/di-config';
import { JLModelSource } from './sprotty/diagram-server';
import { NodeExpandTool, NodeSelectTool } from './tools';

import {
  IFeedbackActionDispatcher,
  FeedbackActionDispatcher
} from './tools/feedback/feedback-action-dispatcher';
import { ToolTYPES } from './tools/types';

const WIDGET_CLASS = 'jp-ElkView';

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
      value: null,
      _mark_layout: {}
    };
    return defaults;
  }

  initialize(attributes: any, options: any) {
    super.initialize(attributes, options);
    this._elk = new ELK.default({ workerFactory: () => new (Worker as any)() } as any);
    this.on('change:value', this.value_changed, this);
    this.value_changed().catch(err => console.error(err));
  }

  async value_changed() {
    let value = this.get('value');
    if (this._elk && value != null && Object.keys(value).length) {
      let layout = await this._elk.layout(value);
      this.set('_mark_layout', layout);
    }
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

  render() {
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
      console.warn('Failed initial ELK view render', err)
    );
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

  handleMessage(content, buffers) {
    // console.log('custom msg', content, buffers);
    switch (content.action) {
      case 'center': {
        let elementIds: string[];
        if (content.hasOwnProperty('model_id')) {
          if (!Array.isArray(content.model_id)) {
            elementIds = [content.model_id];
          } else {
            elementIds = content.model_id;
          }
        } else {
          elementIds = [];
        }
        this.source.center(elementIds);
      }
    }
  }
}

namespace Private {
  let _next_id = 0;
  export function next_id() {
    return `sprotty_${_next_id++}`;
  }
}
