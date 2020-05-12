import { ContainerModule } from 'inversify';
import {
  configureCommand,
  LocationPostprocessor,
  MoveCommand,
  TYPES,
  SelectCommand,
  SelectAllCommand,
  GetSelectionCommand
} from 'sprotty/lib';
import { ToolTYPES } from '../types';
import { ApplyCursorCSSFeedbackActionCommand } from './cursor-feedback';
import { FeedbackActionDispatcher } from './feedback-action-dispatcher';

const toolFeedbackModule = new ContainerModule((bind, _unbind, isBound) => {
  bind(ToolTYPES.IFeedbackActionDispatcher)
    .to(FeedbackActionDispatcher)
    .inSingletonScope();

  // create node and edge tool feedback
  configureCommand({ bind, isBound }, ApplyCursorCSSFeedbackActionCommand);
  configureCommand({ bind, isBound }, MoveCommand);

  //Select commands
  configureCommand({ bind, isBound }, SelectCommand);
  configureCommand({ bind, isBound }, SelectAllCommand);
  configureCommand({ bind, isBound }, GetSelectionCommand);

  bind(TYPES.IVNodePostprocessor).to(LocationPostprocessor);
  bind(TYPES.HiddenVNodePostprocessor).to(LocationPostprocessor);
});

export default toolFeedbackModule;
