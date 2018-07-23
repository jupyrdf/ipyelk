declare module 'elkjs/lib/elk.bundled.js' {
    // export class ELK {
    //     layout(graph:object, options:object):Promise<object>;
    //
    // }
    // export enum

    export interface IELKOptions {
        // workerUrl?: string;
    }

    export default class ELK implements IELK {
        constructor(config: IELKOptions);
        layout(graph: object, options: object): Promise<object>;
    }
}
