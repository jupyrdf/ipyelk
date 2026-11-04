# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline


class _Copy(Pipe):
    """A stage whose output is a new tree, as a ``VisibilityPipe`` projection is."""

    async def run(self):
        self.outlet.value = self.inlet.value.model_copy()


def test_empty_pipeline_check_does_not_raise():
    pipeline = Pipeline(pipes=[])
    assert pipeline.check() is True


def test_empty_pipeline_progress_is_complete():
    pipeline = Pipeline(pipes=[])
    assert pipeline.get_progress_value() == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_a_clean_stage_keeps_its_output_until_its_input_changes():
    """A clean stage keeps what it made from an unchanged input, and passes a new
    input through (#231).
    """
    first, second = _Copy(observes=("a",)), _Copy(observes=("b",))
    source = MarkElementWidget(value=Node(id="root"))
    pipeline = Pipeline(inlet=source)
    pipeline.pipes = [first, second]
    pipeline.inlet.record("a", "b")
    await pipeline.run()
    made = pipeline.outlet.value
    assert made is not first.outlet.value

    await pipeline.run()  # nothing pending
    assert pipeline.outlet.value is made

    pipeline.inlet.record("a")
    await pipeline.run()
    assert pipeline.outlet.value is first.outlet.value, "a new input passes through"
    pipeline.close()
    source.close()


@pytest.mark.asyncio
async def test_a_clean_copy_does_not_hide_an_edit_it_does_not_observe():
    """A change report that no stage observes may be an in-place edit: a clean
    stage that copies passes its input on, not its stale copy.
    """
    root = Node(id="root")
    source = MarkElementWidget(value=root)
    pipeline = Pipeline(inlet=source)
    pipeline.pipes = [_Copy(observes=("a",))]
    pipeline.inlet.record("a")
    await pipeline.run()
    assert pipeline.outlet.value is not root

    root.layoutOptions = {"org.eclipse.elk.direction": "DOWN"}
    pipeline.inlet.record("b")
    await pipeline.run()
    assert pipeline.outlet.value is root
    pipeline.close()
    source.close()


@pytest.mark.asyncio
async def test_a_new_stage_after_a_stage_that_kept_passes_its_input_on():
    """A stage that never ran has no output to keep, so it passes its input on."""
    first, second = _Copy(observes=("a",)), _Copy(observes=("a",))
    source = MarkElementWidget(value=Node(id="root"))
    pipeline = Pipeline(inlet=source)
    pipeline.pipes = [first]
    pipeline.inlet.record("a")
    await pipeline.run()

    pipeline.pipes = [first, second]
    await pipeline.run()  # nothing pending: the first stage keeps its output
    assert pipeline.outlet.value is first.outlet.value
    pipeline.close()
    source.close()
