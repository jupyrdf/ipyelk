/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import {
  Action,
  CenterAction,
  FitToScreenAction,
  HoverFeedbackAction,
  SModelElement,
  SModelRoot,
  SelectAction,
  SelectionResult, // SModelRegistry,
  SetModelAction,
  SetViewportAction,
  UpdateModelAction,
} from 'sprotty-protocol';

// import { WidgetManager } from '@jupyter-widgets/jupyterlab-manager';
// import { ManagerBase } from '@jupyter-widgets/base';
import {
  ActionDispatcher,
  ActionHandlerRegistry, // IModelFactory,
  CommandStackOptions,
  InitializeCanvasBoundsAction, // SModelFactory,
  TYPES,
} from 'sprotty';

import { PromiseDelegate, UUID } from '@lumino/coreutils';
import { Message } from '@lumino/messaging';
import { Signal } from '@lumino/signaling';
import { Widget } from '@lumino/widgets';

import {
  DOMWidgetModel,
  DOMWidgetView,
  WidgetModel,
  WidgetView,
  unpack_models as deserialize,
} from '@jupyter-widgets/base';

import { hoverAfterFeedback, hoverFeedbackActions } from './hover_util';
import {
  canonicalSelection,
  selectionAfterLayout,
  selectionDelta,
} from './selection_util';
import createContainer from './sprotty/di-config';
import { JLModelSource } from './sprotty/diagram-server';
import { PainterStyles } from './sprotty/json/elkgraph-to-sprotty';
// import { VNode } from 'snabbdom';
import { ELK_CSS, ELK_DEBUG, NAME, TAnyELKMessage, VERSION } from './tokens';
import { NodeExpandTool, NodeSelectTool } from './tools';
import {
  FeedbackActionDispatcher,
  IFeedbackActionDispatcher,
} from './tools/feedback/feedback-action-dispatcher';
import { ToolTYPES } from './tools/types';
import {
  IViewportReport,
  ViewportReporter,
  modelIds,
  viewedIds,
  viewportRect,
} from './viewport_util';

const POLL = 300;
/**
 * Maximum interval for browser-side recovery probes. These are rate-capped,
 * not time-limited: they stop when a source becomes renderable or the view
 * disconnects. Pipe deadlines are separate.
 */
// trailing debounce for viewport reports: a wheel/drag burst -> one kernel write
const VIEWPORT_DEBOUNCE = 100;
const STALE_DELAY_MAX = 10000;

export class ELKControlModel extends DOMWidgetModel {
  static model_name = 'ELKControlModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    overlay: { deserialize },
  };

  defaults() {
    let defaults = {
      ...super.defaults(),

      _model_name: ELKControlModel.model_name,
      _model_module_version: VERSION,
      //    _view_module: NAME,
      //    _view_name: ELKViewerView.view_name,
      //    _view_module_version: VERSION,
      overlay: null,
    };
    return defaults;
  }
}

export class ELKViewerModel extends DOMWidgetModel {
  static model_name = 'ELKViewerModel';
  static serializers = {
    ...DOMWidgetModel.serializers,
    source: { deserialize },
    selection: { deserialize },
    hover: { deserialize },
    painter: { deserialize },
    viewport: { deserialize },
    control_overlay: { deserialize },
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
      source: null,
      control_overlay: null,
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
  // toolManager: ToolManager;
  registry: ActionHandlerRegistry;
  actionDispatcher: ActionDispatcher;
  feedbackDispatcher: IFeedbackActionDispatcher;
  // elementRegistry: SModelRegistry;
  currentRoot: SModelRoot;
  was_shown = new PromiseDelegate<void>();
  /**
   * A kernel-side selection that arrived before the first layout was
   * submitted; replayed after `diagramLayout` creates the Sprotty model.
   */
  private pendingSelected: string[] | null = null;
  /**
   * Source whose `change:value` listener is currently connected. This stays
   * unset until initialization completes because Backbone calls `initialize`
   * from `super()`, and a field initializer would overwrite that source.
   */
  private connectedSource: DOMWidgetModel | null | undefined;
  /** Hover tool whose `change:hovered_id` this view observes. */
  private connectedHover: DOMWidgetModel | null | undefined;
  /** Painter whose `change:styles` this view observes. */
  private connectedPainter: WidgetModel | null | undefined;
  /** Identifies this view in viewport reports and `set_viewport` commands. */
  readonly view_id: string = UUID.uuid4();
  private viewportReportTimer: number | null = null;
  /** Coalesces viewport snapshots before writing meaningful changes to the tool. */
  private readonly viewportReporter = new ViewportReporter(
    () => this.gatherViewport(),
    (report) => {
      const viewport: WidgetModel = this.model.get('viewport');
      viewport.set(report);
      viewport.save_changes();
    },
  );
  /** Sprotty animation length; animated viewport actions settle after this delay. */
  private animationDuration = 0;

  initialize(parameters: WidgetView.IInitializeParameters) {
    super.initialize(parameters);
    this.luminoWidget.addClass(ELK_CSS.widget_class);
    // `change:source` fires on the MODEL: subscribing on the view (`this.on`)
    // is a channel nobody triggers, so a source wired after view-init never
    // attached its change:value listener and the diagram stayed blank.
    // listenTo: `remove()` -> `stopListening()` cleans up with the view.
    this.listenTo(this.model, 'change:source', this.on_source_changed);
    this.on_source_changed();
  }
  async on_source_changed() {
    let source = this.model.get('source');
    if (source === this.connectedSource) {
      return;
    }
    // exactly one live value listener: drop the previous source's
    if (this.connectedSource) {
      this.stopListening(this.connectedSource, 'change:value');
    }
    this.connectedSource = source;
    if (source) {
      this.listenTo(source, 'change:value', this.diagramLayout);
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
    if (!this.luminoWidget.isVisible) {
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
    this.source.diagramWidget = this;
    this.source.widget_manager = this.model.widget_manager as any;
    this.source.factory = container.get(TYPES.IModelFactory);
    // this.toolManager = container.get<ToolManager>(TYPES.IToolManager);
    this.registry = container.get<ActionHandlerRegistry>(ActionHandlerRegistry);
    this.actionDispatcher = container.get<ActionDispatcher>(TYPES.IActionDispatcher);
    this.feedbackDispatcher = container.get<FeedbackActionDispatcher>(
      ToolTYPES.IFeedbackActionDispatcher,
    );
    this.animationDuration = container.get<CommandStackOptions>(
      TYPES.CommandStackOptions,
    ).defaultDuration;
    // this.model.on('change:mark_layout', this.diagramLayout, this);
    this.model.on('change:selection', this.updateSelectedTool, this);
    this.model.on('change:hover', this.updateHoverTool, this);
    this.model.on('change:painter', this.updatePainterTool, this);
    this.model.on('change:interaction', this.interaction_mode_changed, this);
    this.model.on('msg:custom', this.handleMessage, this);
    this.model.on('change:symbols', this.diagramLayout, this);
    this.model.on('change:control_overlay', this.updateControlOverlay, this);

    // init for the first time
    this.updateSelectedTool();
    this.updateHoverTool();
    this.updatePainterTool();
    this.updateControlOverlay();

    this.touch(); //to sync back the diagram state

    // Register Action Handlers
    this.registry.register(SelectAction.KIND, this);
    this.registry.register(SelectionResult.KIND, this); //sprotty complains if doesn't have a SelectionResult handler
    this.registry.register(HoverFeedbackAction.KIND, this);

    // getting hook for
    this.registry.register(SetModelAction.KIND, this);
    this.registry.register(UpdateModelAction.KIND, this);
    // every way the camera or canvas can change reports the viewport
    this.registry.register(SetViewportAction.KIND, this);
    this.registry.register(CenterAction.KIND, this);
    this.registry.register(FitToScreenAction.KIND, this);
    this.registry.register(InitializeCanvasBoundsAction.KIND, this);

    // Register Tools
    // this.toolManager.registerDefaultTools(
    container.resolve(NodeSelectTool).enable();
    container.resolve(NodeExpandTool).enable();
    // );
    // this.toolManager.enableDefaultTools();

    this.diagramLayout().catch((err) =>
      console.warn('ELK Failed initial view render', err),
    );
    // the `source` reference arrives as a state update AFTER comm-open and
    // jupyter-server's iopub rate limiter silently drops state updates
    // under bursty load; a view left watching a missing/empty source stayed
    // blank forever. Report the stale state (with backoff) until renderable
    // so the kernel re-syncs the wiring (Viewer._handle_browser_msg).
    this.scheduleStaleCheck();

    // timeout is ugly workaround for gh issue #94. Still potential for bounding
    // box being stale but added resize call to the `fit` and `center` actions
    // as additional protection.
    setTimeout(() => {
      this.resize();
    }, 10 * POLL);
  }

  updateControlOverlay() {
    const overlay: WidgetModel | null = this.model.get('control_overlay');
    const previous = this.source.control_overlay;
    if (previous && previous !== overlay) {
      this.stopListening(previous, 'change:children');
    }
    this.source.control_overlay = overlay;
    if (overlay) {
      // the container is only rendered for a non-empty overlay, and the kernel
      // usually fills `children` AFTER the selection render that would show
      // it: re-render when the overlay gains or loses its children
      this.listenTo(overlay, 'change:children', this.rerenderControlOverlay);
    }
    // swapping the overlay (or clearing it to None) must show the new one and
    // take the old one off screen; only `change:children` re-rendered before.
    // A no-op before the first layout (nothing to render yet).
    this.rerenderControlOverlay();
  }

  rerenderControlOverlay() {
    if (this.source?.index == null) {
      return; // nothing submitted yet; the first layout renders the overlay
    }
    this.source.updateModel().catch((err) => {
      console.warn('ELK failed to re-render the control overlay', err);
    });
  }

  /** Delay (ms) before the next stale-state check; doubles per silent retry. */
  private staleDelay = 2000;

  /**
   * Report a non-renderable viewer state and retry with exponential backoff.
   * This acts as a state-recovery handshake for dropped widget updates; it is
   * deliberately kept in the frontend because it paces browser-to-kernel
   * transport rather than diagram layout.
   */
  scheduleStaleCheck() {
    setTimeout(() => {
      if (!this.el.isConnected) {
        return; // the view was removed; a live sibling view owns the pump
      }
      const source = this.model.get('source');
      if (source != null && source.get('value') != null) {
        return; // renderable: the change:value wiring takes it from here
      }
      ELK_DEBUG && console.warn('ELK viewer reporting stale source');
      this.model.send(
        { action: 'stale', missing: { source: source == null, value: true } },
        {},
      );
      this.staleDelay = Math.min(this.staleDelay * 2, STALE_DELAY_MAX);
      this.scheduleStaleCheck();
    }, this.staleDelay);
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
    this.processLuminoMessage(msg);
  }

  processLuminoMessage(msg: Message): void {
    super.processLuminoMessage(msg);
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

  // The selection write-back below is ASYNC (getSelection resolves one
  // action-queue slot later), so two SelectActions dispatched close
  // together each read the OTHER action's resulting state and write it
  // back, flipping the selection tool's `ids` forever: a self-sustaining
  // microtask oscillation that pegs the renderer main thread.  The
  // generation stamp drops every superseded gather; only the LATEST
  // SelectAction's write-back lands, which by construction matches the
  // final sprotty state.
  //
  // The stamp is per VIEW, and `change:ids` is observed by EVERY view of a
  // shared diagram model, so it cannot see a write-back bouncing between two
  // views (a linked output view, 03_App): each side legitimately sees a new
  // gather. `selectionDelta`/`canonicalSelection` close that door by making
  // the write-back set-based and order-independent, so a reordering is not a
  // change and there is nothing to bounce.
  private selectionWriteBackGen = 0;

  handle(action: Action) {
    switch (action.kind) {
      case SelectAction.KIND:
        const writeBackGen = ++this.selectionWriteBackGen;
        this.source.getSelection().then((selection) => {
          if (writeBackGen !== this.selectionWriteBackGen) {
            return; // a newer SelectAction superseded this gather
          }
          let ids = [];
          let nodes = [];
          selection.forEach((node, i) => {
            ids.push(node.id);
            nodes.push(node);
          });
          let selectionTool = this.model.get('selection');
          if (selectionTool != null) {
            const next = canonicalSelection(ids);
            this.setSelectedNodes(next);
            if (!selectionDelta(selectionTool.get('ids'), next).changed) {
              return; // same selection, possibly gathered in another order
            }
            selectionTool.set('ids', next);
            selectionTool.save_changes();
            this.model.diagramUpdated.emit(void 0);
          }
        });
        break;
      case SelectionResult.KIND:
        break;
      case HoverFeedbackAction.KIND:
        const hoverFeedback = action as HoverFeedbackAction;
        const hover = this.model.get('hover');
        if (hover != null) {
          const current: string | null = hover.get('hovered_id');
          const next = hoverAfterFeedback(current, hoverFeedback);
          // the feedback this view itself dispatches from updateHover lands
          // here too: an unchanged id is written back to nothing
          if (next !== current) {
            hover.set('hovered_id', next);
            hover.save_changes();
            this.model.diagramUpdated.emit(void 0);
          }
        }
        break;
      case SetModelAction.KIND:
        let setModelAction: SetModelAction = action as SetModelAction;
        const { newRoot } = setModelAction;
        if (newRoot) {
          this.currentRoot = newRoot;
        }
        break;
      case UpdateModelAction.KIND:
        break;
      case SetViewportAction.KIND:
      case CenterAction.KIND:
      case FitToScreenAction.KIND:
        // the handler runs when the action is dispatched; an animated move only
        // settles after sprotty's animation, so report once that has ended
        const { animate } = action as
          | SetViewportAction
          | CenterAction
          | FitToScreenAction;
        this.scheduleViewportReport(animate ? this.animationDuration : 0);
        break;
      case InitializeCanvasBoundsAction.KIND:
        this.scheduleViewportReport();
        break;
      default:
        break;
    }
  }

  /** Report the viewport `VIEWPORT_DEBOUNCE` ms (plus `extra`) after the last trigger. */
  scheduleViewportReport(extra = 0) {
    if (this.viewportReportTimer != null) {
      window.clearTimeout(this.viewportReportTimer);
    }
    this.viewportReportTimer = window.setTimeout(() => {
      this.viewportReportTimer = null;
      this.reportViewport().catch((err) =>
        console.warn('ELK failed to report the viewport', err),
      );
    }, VIEWPORT_DEBOUNCE + extra);
  }

  /**
   * Write this view's camera and the ids it shows to the kernel's `Viewer.viewport`
   * as ONE state update; the reporter drops superseded gathers and snapshots the
   * kernel could not tell from the last one.
   */
  async reportViewport(): Promise<void> {
    if (this.model.get('viewport') == null) {
      return;
    }
    await this.viewportReporter.report();
  }

  /** This view's snapshot, or null while it is detached or has nothing rendered. */
  private async gatherViewport(): Promise<IViewportReport | null> {
    const layout = this.model.get('source')?.get('value');
    if (!this.el.isConnected || layout == null || this.source?.index == null) {
      return null;
    }
    const { scroll, zoom, canvasBounds } = await this.source.getViewport();
    const rect = viewportRect(scroll, zoom, canvasBounds);
    return {
      view_id: this.view_id,
      origin: [scroll.x, scroll.y],
      zoom,
      canvas_size: [canvasBounds.width, canvasBounds.height],
      viewed_ids: viewedIds(this.source.root, rect, modelIds(layout)),
    };
  }

  remove() {
    if (this.viewportReportTimer != null) {
      window.clearTimeout(this.viewportReportTimer);
      this.viewportReportTimer = null;
    }
    return super.remove();
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
      if (this.source?.index == null) {
        // the kernel can set selection ids before the first layout has been
        // submitted (a comm set_state racing initSprotty / diagramLayout):
        // there is no sprotty model or index to select against yet. Queue
        // the ids; diagramLayout replays them once the first model lands.
        this.pendingSelected = selected;
        ELK_DEBUG &&
          console.log('ELK queueing selection before first layout', selected);
        return;
      }
      this.pendingSelected = null; // a live selection supersedes any queued one
      let old_selected: string[] = selection.previous('ids');
      const { entering, exiting, changed } = selectionDelta(old_selected, selected);
      this.setSelectedNodes(selected);
      if (!changed) {
        // nothing entered or left: dispatching would only feed the write-back
        return;
      }
      await this.actionDispatcher.dispatch(
        SelectAction.create({
          selectedElementsIDs: entering,
          deselectedElementsIDs: exiting,
        }),
      );
      this.model.diagramUpdated.emit(void 0);
    }
  }

  /*
   * Keep reference of the current selected nodes on the selection widget
   */
  async setSelectedNodes(selected: string[]) {
    const index = this.source?.index;
    if (index == null) {
      // no model submitted yet (or a disposed view's zombie listener):
      // there is nothing to map the ids against
      ELK_DEBUG &&
        console.log('ELK skipping setSelectedNodes: no model index', selected);
      return;
    }
    // the index holds the submitted schema elements (SModelElement), not the
    // rendered Impl instances; the renderer resolves those by id. Ids the
    // kernel knows but the model does not resolve to nothing: drop them.
    this.source.selectedNodes = selected
      .map((id) => index.getById(id))
      .filter((element): element is SModelElement => element != null);
  }

  updateHoverTool() {
    const hover = this.model.get('hover');
    if (hover === this.connectedHover) {
      return;
    }
    // exactly one live listener: drop the previous tool's (`.on` outlived
    // both the tool swap and the view; listenTo is released by `remove()`)
    if (this.connectedHover) {
      this.stopListening(this.connectedHover, 'change:hovered_id');
    }
    this.connectedHover = hover;
    if (hover != null) {
      this.listenTo(hover, 'change:hovered_id', this.updateHover);
    }
  }

  async updateHover() {
    const hover = this.model.get('hover');
    if (hover != null) {
      const hovered: string | null = hover.get('hovered_id');
      const previous: string | null = hover.previous('hovered_id');
      await this.actionDispatcher.dispatchAll(hoverFeedbackActions(previous, hovered));
      this.model.diagramUpdated.emit(void 0);
    }
  }

  updatePainterTool() {
    const painter: WidgetModel | null = this.model.get('painter');
    if (painter === this.connectedPainter) {
      return;
    }
    if (this.connectedPainter) {
      this.stopListening(this.connectedPainter, 'change:styles');
    }
    this.connectedPainter = painter;
    if (painter != null) {
      // painted classes are merged at transform time, so a paint is a re-render of
      // the SAME layout: sprotty's update keeps selection, hover feedback and the
      // camera, and the kernel value (the model) is never touched
      this.listenTo(painter, 'change:styles', this.diagramLayout);
    }
  }

  /** The kernel `Painter.styles`, `{}` without a painter. */
  painterStyles(): PainterStyles {
    const painter: WidgetModel | null = this.model.get('painter');
    const styles: PainterStyles | undefined = painter?.get('styles');
    return styles == null ? {} : styles;
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
    await this.source.updateLayout(layout, symbols, this.div_id, this.painterStyles());
    // Apply kernel selection on the initial model and on structural replacements.
    // Ordinary coordinate-only updates already retain sprotty selection.
    const selected = selectionAfterLayout(
      this.pendingSelected,
      this.model.get('selection')?.get('ids'),
      (id) => this.source.getById(id) != null,
    );
    this.pendingSelected = null;
    this.setSelectedNodes(selected); // [] when every selected id is gone
    if (selected.length) {
      await this.actionDispatcher.dispatch(
        SelectAction.create({
          selectedElementsIDs: selected,
          deselectedElementsIDs: [],
        }),
      );
    }
    this.model.layoutUpdated.emit();
    this.model.diagramUpdated.emit();
    // a re-layout moves elements under a camera that did not change: re-report
    this.scheduleViewportReport();
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
        this.resize(); // ensure bounds are accurate before centering
        this.source.center(
          this.normalizeElementIds(content.model_id),
          content.animate,
          content.retain_zoom,
        );
        break;
      case 'fit':
        this.resize(); // ensure bounds are accurate before fitting
        this.source.fit(
          this.normalizeElementIds(content.model_id),
          content.padding == null ? 0 : content.padding,
          content.max_zoom == null ? Infinity : content.max_zoom,
          content.animate == null ? true : content.animate,
        );
        break;
      case 'viewport':
        if (content.view_id != null && content.view_id !== this.view_id) {
          break; // addressed to another view of this diagram
        }
        this.resize(); // ensure bounds are accurate before moving
        this.source
          .setViewport(content.origin, content.zoom, content.animate)
          .catch((err) => console.warn('ELK failed to set the viewport', err));
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
