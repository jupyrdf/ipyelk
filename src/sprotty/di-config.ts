/*******************************************************************************
 * Copyright (c) 2017 TypeFox GmbH (http://www.typefox.io) and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *******************************************************************************/

import {
    DOMWidgetView,
} from '@jupyter-widgets/base';

import { Container, ContainerModule } from "inversify";
import {
    TYPES, defaultModule, 
    boundsModule, fadeModule, viewportModule,
    moveModule, 
    // hoverModule,
    // Tool,
    // MouseTool,
    exportModule, SGraphView, ConsoleLogger, LogLevel, configureViewerOptions, SvgExporter, configureModelElement,
    SGraph, SGraphFactory, SLabel, edgeEditModule, undoRedoModule, updateModule, routingModule, modelSourceModule, labelEditModule,
    ICommandStack, 
    // ToolManager, DefaultToolsEnablingKeyListener, ToolManagerActionHandler,
    EnableToolsAction,
    // EnableDefaultToolsAction,
    // configureActionHandler,
    HoverFeedbackCommand,
    configureCommand,
    // HoverFeedbackAction
    // LocalModelSource,
} from "sprotty";

import { JLModelSource } from "./diagram-server";
import { ElkNodeView, ElkPortView, ElkEdgeView, ElkLabelView, JunctionView } from "./views";
import { ElkNode, ElkPort, ElkEdge, ElkJunction } from "./sprotty-model";
import { NodeSelectTool } from "../tools/select";
import { toolFeedbackModule } from "../tools/feedback";

import _ from 'lodash';

class FilteringSvgExporter extends SvgExporter {
    protected isExported(styleSheet: CSSStyleSheet): boolean {
        return styleSheet.href !== null && (styleSheet.href.endsWith('diagram.css') || styleSheet.href.endsWith('sprotty.css'));
    }
}

export default (containerId: string, view:DOMWidgetView) => {
    const elkGraphModule = new ContainerModule((bind, unbind, isBound, rebind) => {
        bind(TYPES.ModelSource).to(JLModelSource).inSingletonScope();

        rebind(TYPES.ILogger).to(ConsoleLogger).inSingletonScope();
        rebind(TYPES.LogLevel).toConstantValue(LogLevel.warn);
        rebind(TYPES.IModelFactory).to(SGraphFactory).inSingletonScope();
        rebind(TYPES.SvgExporter).to(FilteringSvgExporter).inSingletonScope();
        
        const context = { bind, unbind, isBound, rebind };

        // Initialize model element views
        configureModelElement(context, 'graph', SGraph, SGraphView);
        configureModelElement(context, 'node', ElkNode, ElkNodeView);
        configureModelElement(context, 'port', ElkPort, ElkPortView);
        configureModelElement(context, 'edge', ElkEdge, ElkEdgeView);
        configureModelElement(context, 'label', SLabel, ElkLabelView);
        configureModelElement(context, 'junction', ElkJunction, JunctionView);
        configureViewerOptions(context, {
            needsClientLayout: false,
            baseDiv: containerId,
        });

        // Hover
        configureCommand(context, HoverFeedbackCommand);

        // bind(TYPES.IActionHandlerInitializer).to(MyActionHandlerInitializer)

    })
    const container = new Container();   
    

    container.load(defaultModule, 
         boundsModule,
          moveModule,
           fadeModule,
        //    hoverModule,
        updateModule, undoRedoModule, viewportModule, routingModule, exportModule, modelSourceModule,
        edgeEditModule, labelEditModule, toolFeedbackModule, elkGraphModule);
    

    let jlSource:JLModelSource = container.get(TYPES.ModelSource);
    const commandStack = container.get<ICommandStack>(TYPES.ICommandStack);
    const dispatcher = container.get(TYPES.IActionDispatcher);
    (<any>window).sp = {TYPES, container, defaultModule, EnableToolsAction, dispatcher, NodeSelectTool, commandStack, jlSource};
    (<any>window)._ = _;
    return container;
}