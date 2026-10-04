/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import 'reflect-metadata';
import { expect, it } from 'vitest';

import { UpdateModelAction } from 'sprotty-protocol';

import {
  Animation,
  CommandExecutionContext,
  FadeAnimation,
  SModelRootImpl,
  SNodeImpl,
  UpdateAnimationData,
  easeInOut,
} from 'sprotty';

import { UpdateModelCommand2 } from '../sprotty/update/update-model';

/** Animation frames on demand, at chosen timestamps. */
class Frames {
  private tasks: ((time: number) => void)[] = [];
  isAvailable() {
    return true;
  }
  onNextFrame(task: (time: number) => void) {
    this.tasks.push(task);
  }
  onEndOfNextFrame(task: (time: number) => void) {
    this.tasks.push(task);
  }
  run(time: number) {
    const tasks = this.tasks;
    this.tasks = [];
    tasks.forEach((task) => task(time));
  }
}

class TestCommand extends UpdateModelCommand2 {
  animations(
    data: UpdateAnimationData,
    root: SModelRootImpl,
    context: any,
  ): Animation[] {
    return this.createAnimations(data, root, context);
  }
}

/** a root holding a node that is fading out, and a context driven by `frames` */
function fadingOut() {
  const root = new SModelRootImpl();
  root.id = 'root';
  const gone = new SNodeImpl();
  gone.id = 'gone';
  root.add(gone);
  const frames = new Frames();
  const context = {
    root,
    duration: 250,
    syncer: frames,
    modelChanged: { update: () => undefined },
    logger: { log: () => undefined },
  } as unknown as CommandExecutionContext;
  const data: UpdateAnimationData = { fades: [{ element: gone, type: 'out' }] };
  return { root, gone, frames, context, data };
}

// a frame a hair before the end: the raw time is below 1, the eased time is 1
const NEARLY = 250 * (1 - 2 ** -52);

it('eases a frame just short of the end to exactly 1', () => {
  expect(NEARLY / 250).toBeLessThan(1);
  expect(easeInOut(NEARLY / 250)).toBe(1);
});

it("reproduces sprotty's fade-out removing an element twice", () => {
  const { root, gone, frames, context, data } = fadingOut();
  const fade = new FadeAnimation(root, data.fades, context, true);
  let settled = false;
  fade.start().then(() => (settled = true));
  frames.run(0);
  frames.run(NEARLY);
  expect(root.children).not.toContain(gone);
  expect(() => frames.run(250)).toThrow('No such child gone');
  expect(settled).toBe(false);
});

it('fades out once, however often the last frame runs', async () => {
  const { root, gone, frames, context, data } = fadingOut();
  const command = new TestCommand(
    UpdateModelAction.create({ id: 'root', type: 'graph' }),
  );
  const animations = command.animations(data, root, context);
  expect(animations).toHaveLength(1);
  const done = animations[0].start();
  frames.run(0);
  frames.run(NEARLY);
  frames.run(250);
  await expect(done).resolves.toBe(root);
  expect(root.children).not.toContain(gone);
});
