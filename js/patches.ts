// Addressing issue between reflect-metadata and fast foundation reflect

const KEYSTODELETE = ['defineMetadata', 'getOwnMetadata', 'metadata'];

export async function patchReflectMetadata() {
  if (Reflect.metadata) {
    console.warn('Patching broken fast-foundation Reflect.metadata shim');
  }

  for (const key of KEYSTODELETE) {
    delete Reflect[key];
  }
  await import('reflect-metadata');
}
