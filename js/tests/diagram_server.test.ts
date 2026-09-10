/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { expect, it, vi } from 'vitest';

import { SModelRoot } from 'sprotty-protocol';

import { ActionDispatcher } from 'sprotty';

import { PromiseDelegate } from '@lumino/coreutils';

import { JLModelSource } from '../sprotty/diagram-server';

vi.mock('../tokens', () => ({ ELK_DEBUG: false }));

class TestModelSource extends JLModelSource {
  constructor(override readonly actionDispatcher: ActionDispatcher) {
    super();
  }

  submit(root: SModelRoot): Promise<void> {
    return this.doSubmitModel(root, false);
  }
}

it('waits for model dispatch before reporting submission complete', async () => {
  // Exercise the real superclass submission with a deliberately delayed dispatcher.
  const dispatcher = new ActionDispatcher();
  const pendingDispatch = new PromiseDelegate<void>();
  vi.spyOn(dispatcher, 'dispatch').mockReturnValue(pendingDispatch.promise);
  const source = new TestModelSource(dispatcher);
  let complete = false;
  const submission = source.submit({ id: 'root', type: 'graph' });
  submission.then(() => {
    complete = true;
  });
  await Promise.resolve();
  await Promise.resolve();
  const completedBeforeDispatch = complete;
  pendingDispatch.resolve();
  await submission;
  expect(completedBeforeDispatch).toBe(false);
  expect(complete).toBe(true);
  expect(source.index).toBeDefined();
});
