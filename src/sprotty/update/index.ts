/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 * FIX BELOW FROM:
 * back porting to fix duplicate ids
 * https://github.com/eclipse/sprotty/pull/209/files
 * remove after next sprotty release > 0.9
 */
import { ContainerModule } from 'inversify';
import { configureCommand } from 'sprotty';
import { UpdateModelCommand2 } from './update-model';

const updateModule = new ContainerModule((bind, _unbind, isBound) => {
  configureCommand({ bind, isBound }, UpdateModelCommand2);
});

export default updateModule;
