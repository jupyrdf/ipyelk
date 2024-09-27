/**
 * # Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { NAME } from './tokens';

const KEYSTODELETE = ['defineMetadata', 'getOwnMetadata', 'metadata'];

/**
 * Address issue between reflect-metadata and fast-foundation di
 */
export async function patchReflectMetadata(): Promise<void> {
  if (Reflect.hasOwnMetadata != null) {
    console.info(`${NAME}: skipping patch of Reflect.metadata`);
    return;
  }
  if (Reflect.metadata) {
    console.warn(`${NAME}: patching broken fast-foundation Reflect.metadata shim`);
  }

  for (const key of KEYSTODELETE) {
    delete Reflect[key];
  }
  await import('reflect-metadata');
}
