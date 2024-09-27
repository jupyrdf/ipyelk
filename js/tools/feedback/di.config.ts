/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { ContainerModule } from 'inversify';

import {
  GetSelectionCommand,
  LocationPostprocessor,
  MoveCommand,
  SelectAllCommand,
  SelectCommand,
  TYPES,
  configureCommand,
} from 'sprotty/lib';

import { ToolTYPES } from '../types';

import { ApplyCursorCSSFeedbackActionCommand } from './cursor-feedback';
import { FeedbackActionDispatcher } from './feedback-action-dispatcher';

const toolFeedbackModule = new ContainerModule((bind, unbind, isBound, rebind) => {
  const context = { bind, isBound };
  bind(ToolTYPES.IFeedbackActionDispatcher)
    .to(FeedbackActionDispatcher)
    .inSingletonScope();

  // create node and edge tool feedback
  configureCommand(context, ApplyCursorCSSFeedbackActionCommand);
  configureCommand(context, MoveCommand);

  //Select commands
  configureCommand(context, SelectCommand);
  configureCommand(context, SelectAllCommand);
  configureCommand(context, GetSelectionCommand);

  bind(TYPES.IVNodePostprocessor).to(LocationPostprocessor);
  bind(TYPES.HiddenVNodePostprocessor).to(LocationPostprocessor);
});

export default toolFeedbackModule;
