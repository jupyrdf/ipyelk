# Pipes

## Rendering lifecycle recovery

Widget state can arrive out of order, and an overloaded Jupyter server can drop a state
update. The browser therefore reports a _stale_ pipe or viewer instead of waiting
indefinitely; the kernel re-emits the relevant widget state with bounded exponential
backoff. This is a recovery handshake, not a rendering timeout: it stops as soon as the
browser has a renderable source.

```{mermaid}
sequenceDiagram
    participant K as Kernel
    participant B as Browser
    K->>B: widget state / run request
    alt inlet, value, or outlet missing
        B->>K: stale (which state is missing)
        K->>B: re-emit endpoint and pipe/viewer state
    else state is renderable
        B->>B: render layout and selection
    end
```

```{eval-rst}
.. currentmodule:: ipyelk.pipes
.. autoclass:: ipyelk.pipes.Pipe
    :members:
.. autoclass:: ipyelk.pipes.Pipeline
    :members:
.. autoclass:: ipyelk.pipes.base.PipeStatus
    :members:
.. autoclass:: ipyelk.pipes.base.PipeStatusView
    :members:
```

```{eval-rst}
.. currentmodule:: ipyelk.pipes
.. autoclass:: ipyelk.pipes.MarkElementWidget
    :members:

```

```{eval-rst}
.. currentmodule:: ipyelk.pipes
.. autoclass:: ipyelk.pipes.ElkJS
    :members:
```
