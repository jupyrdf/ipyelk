/**
 * Copyright (c) 2024 ipyelk contributors.
 * Distributed under the terms of the Modified BSD License.
 */
import { ElkGraphElement, ElkNode, ElkProperties } from './sprotty/json/elkgraph-json';

export function layoutErrorMessage(error: unknown): { action: 'error'; error: string } {
  return { action: 'error', error: `${error}` };
}

export type TStaleMessage = {
  action: 'stale';
  missing: { inlet: boolean; value: boolean; outlet: boolean };
};

/**
 * The browser -> kernel report for a `run` request the pipe model cannot
 * serve: its inlet / inlet value / outlet never arrived. jupyter-server's
 * iopub rate limiter silently drops `comm_msg` under bursty load and the
 * widget protocol has no retransmit. Without this report, retries cannot
 * repair missing state before the roundtrip deadline. The kernel answers
 * `stale` by re-sending the widget state.
 * Returns `null` when the model IS servable.
 */
export function staleMessage(
  inlet: unknown,
  value: unknown,
  outlet: unknown,
): TStaleMessage | null {
  if (value != null && outlet != null) {
    return null;
  }
  return {
    action: 'stale',
    missing: { inlet: inlet == null, value: value == null, outlet: outlet == null },
  };
}

type TProperties = Record<string, ElkProperties | undefined>;
type ElkElementWithChildren = ElkGraphElement & {
  children?: ElkNode[];
  ports?: ElkGraphElement[];
  edges?: ElkGraphElement[];
};

/**
 * Collect the `properties` of every graph element into a map keyed by
 * element id, removing them from the element IN PLACE. elkjs fails to
 * process edge properties that are anything more than simple strings, and it
 * does not need them: they carry ipyelk -> sprotty data (e.g. `cssClasses`),
 * so they are stripped before layout and reapplied afterwards.
 */
export function collectProperties(node: ElkNode): TProperties {
  let props: TProperties = {};

  function strip(node: ElkElementWithChildren) {
    props[node.id] = node.properties;
    delete node['properties'];
    // children
    if (node.children) {
      node.children.map(strip);
    }
    // ports
    if (node.ports) {
      node.ports.map(strip);
    }
    // labels
    if (node.labels) {
      node.labels.map(strip);
    }
    // edges
    if (node.edges) {
      node.edges.map(strip);
    }
  }
  strip(node);
  return props;
}

/** Reapply properties collected by {@link collectProperties} onto a layout result. */
export function applyProperties(node: ElkNode, props: TProperties): ElkNode {
  function apply(node: ElkElementWithChildren) {
    node.properties = props[node.id];

    // children
    if (node.children) {
      node.children.map(apply);
    }
    // ports
    if (node.ports) {
      node.ports.map(apply);
    }
    // labels
    if (node.labels) {
      node.labels.map(apply);
    }
    // edges
    if (node.edges) {
      node.edges.map(apply);
    }
  }
  apply(node);
  return node;
}

/**
 * Prepare a graph for elkjs layout without mutating the caller's graph.
 *
 * {@link collectProperties} strips properties in place; running it directly
 * on the shared inlet value made `ELKLayoutModel.layout()` non-idempotent: a
 * duplicate `run` message or an overlapping refresh laid out an
 * already-stripped graph and pushed a layout carrying no `cssClasses` -- the
 * diagram rendered styled, then flipped to unstyled moments later. Deep
 * copying first keeps the inlet value intact, so `layout()` may run any
 * number of times.
 */
export function prepareGraphForElk(rootNode: ElkNode): {
  graph: ElkNode;
  propmap: TProperties;
} {
  const graph: ElkNode = JSON.parse(JSON.stringify(rootNode));
  return { graph, propmap: collectProperties(graph) };
}

export type TRunDisposition = 'started' | 'queued' | 'ignored';

/**
 * At most one browser computation in flight per pipe, keyed by the kernel's
 * roundtrip generation (`IRunMessage.gen`).
 *
 * The kernel re-sends `run` with backoff until it is answered
 * (`browser_roundtrip`), so a layout slower than the resend interval used to
 * be computed once per resend and the diagram re-rendered on each result. A
 * request for the in-flight (or an older) generation is the same work and is
 * ignored; a newer generation is queued and started once, when the current
 * computation resolves, and only the newest queued generation survives. A
 * request without a generation (an older kernel) coalesces into at most one
 * trailing run. `start` must never be allowed to wedge the queue: a rejected
 * or throwing `start` is logged and the queue moves on.
 */
export class RunQueue {
  private inFlight: number | null = null;
  private queued: number | null = null;

  constructor(private readonly start: (gen: number) => Promise<unknown> | unknown) {}

  /** the generation being computed, if any */
  get current(): number | null {
    return this.inFlight;
  }

  /** the generation waiting for the current computation, if any */
  get pending(): number | null {
    return this.queued;
  }

  request(gen?: number | null): TRunDisposition {
    const wanted = gen ?? 0;
    if (this.inFlight == null) {
      this.launch(wanted);
      return 'started';
    }
    const duplicate =
      wanted > 0
        ? wanted <= Math.max(this.inFlight, this.queued ?? 0)
        : this.queued != null;
    if (duplicate) {
      return 'ignored';
    }
    this.queued = wanted;
    return 'queued';
  }

  private launch(gen: number): void {
    this.inFlight = gen;
    let result: Promise<unknown>;
    try {
      result = Promise.resolve(this.start(gen));
    } catch (error) {
      result = Promise.reject(error);
    }
    result
      .catch((error) => console.error('ELK run failed:', error))
      .then(() => this.finish());
  }

  private finish(): void {
    this.inFlight = null;
    const next = this.queued;
    this.queued = null;
    if (next != null) {
      this.launch(next);
    }
  }
}
