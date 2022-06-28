/**
 * Copyright (c) 2022 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
export const ToolTYPES = {
  IFeedbackActionDispatcher: Symbol.for('IFeedbackActionDispatcher'),
  IToolFactory: Symbol.for('Factory<Tool>'),
  IEditConfigProvider: Symbol.for('IEditConfigProvider'),
  RequestResponseSupport: Symbol.for('RequestResponseSupport'),
  SelectionService: Symbol.for('SelectionService'),
  SelectionListener: Symbol.for('SelectionListener'),
  SModelRootListener: Symbol.for('SModelRootListener'),
  MouseTool: Symbol.for('MouseTool'),
  ViewerOptions: Symbol.for('ViewerOptions')
};
