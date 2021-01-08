/**
 * Copyright (c) 2021 Dane Freeman.
 * Distributed under the terms of the Modified BSD License.
 */
declare module '!!worker-loader!*.js' {}
declare module '!!raw-loader!*.css' {
  export default content as string;
}
